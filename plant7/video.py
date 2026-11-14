"""VSS style video segmentation, local physical reasoning, and caption retrieval."""
import datetime as dt
import hashlib
import json
import os
import shlex
from pathlib import Path

import lancedb
import av

from .audit import run
from .clients import complete, embeddings, json_content
from .settings import MANIFEST, MODELS, ROOT

MEDIA_NAME = 'p7-media-video-v2'


def docker(args):
    return run(['sg', 'docker', '-c', shlex.join(['docker'] + args)])


def ensure_media_container():
    try:
        status = json.loads(docker(['inspect', MEDIA_NAME]))[0]
        if status.get('Config', {}).get('Labels', {}).get('p7.project') != str(ROOT):
            raise ValueError('Existing p7-media container does not belong to this project')
        if not status['State']['Running']:
            docker(['start', MEDIA_NAME])
        return
    except RuntimeError as error:
        if 'no such' not in str(error).lower():
            raise
    docker(['run', '-d', '--name', MEDIA_NAME, '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}',
            '--label', 'p7.project=' + str(ROOT), '-v', str(ROOT / 'data/video') + ':/project/data/video',
            '--entrypoint', '/bin/sh', MANIFEST['image'], '-c', 'while :; do sleep 3600; done'])


def container_path(path):
    return '/project/' + str(Path(path).resolve().relative_to(ROOT))


def validate_media(path):
    path = Path(path).resolve()
    path.relative_to((ROOT / 'data/video').resolve())
    if path.suffix.lower() != '.mp4' or not path.is_file():
        raise ValueError('Existing project-local MP4 required')
    if path.stat().st_size > 2 * 1024**3:
        raise ValueError('Video exceeds 2 GiB project ingest limit')
    with av.open(str(path)) as media:
        stream = media.streams.video[0]
        next(media.decode(video=0))  # Validate actual decodable pixels, not only the extension.
        return {'file': str(path.relative_to(ROOT)), 'width': stream.width, 'height': stream.height,
                'fps': float(stream.average_rate) if stream.average_rate else None,
                'duration_s': float(media.duration) / av.time_base if media.duration else None}


def chunk_video(path):
    """Reencode so segment boundaries are independent of source keyframe spacing."""
    validate_media(path)
    path = Path(path).resolve()
    path.relative_to(ROOT / 'data/video')
    if path.suffix.lower() != '.mp4':
        raise ValueError('MP4 input required')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(8 * 1024 * 1024):
            digest.update(block)
    key = digest.hexdigest()[:16]
    directory = ROOT / 'data/video/chunks' / key
    directory.mkdir(parents=True, exist_ok=True)
    ensure_media_container()
    docker(['exec', MEDIA_NAME, '/usr/bin/ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-i', container_path(path), '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-r', '6', '-g', '12',
            '-force_key_frames', 'expr:gte(t,n_forced*10)', '-f', 'segment', '-segment_time', '10',
            '-reset_timestamps', '1', container_path(directory / 'clip_%03d.mp4')])
    return sorted(directory.glob('clip_*.mp4'))


async def ingest_video(path, line, station, started_at):
    import asyncio
    chunks = await asyncio.to_thread(chunk_video, path)
    start = dt.datetime.fromisoformat(started_at)
    rows = []
    for index, chunk in enumerate(chunks):
        with av.open(str(chunk)) as media:
            duration = (float(media.duration) / av.time_base if media.duration is not None
                        else float(media.streams.video[0].duration * media.streams.video[0].time_base))
        prompt = ('Describe only visible evidence at this torque fixture. Track bolt visitation order, '
                  'operator or tool motion, and any skipped opposite-bolt sequence. Give a short observation '
                  'and uncertainty, with seconds within the clip. A moving marker is an animation, not a real person. '
                  'Do not infer calibration, torque force, or compliance from appearance alone. '
                  'Provide a concise evidence summary, not private reasoning.')
        message, timing = await complete('vision', [{'role': 'user', 'content': [
            {'type': 'video_url', 'video_url': {'url': 'file://' + container_path(chunk)}},
            {'type': 'text', 'text': prompt}]}], max_tokens=800,
            extra_body={'chat_template_kwargs': {'enable_thinking': False},
                        'mm_processor_kwargs': {'fps': 2, 'size': {'shortest_edge': 131072, 'longest_edge': 262144}}})
        caption = message.get('content') or ''
        if not caption:
            raise ValueError('Vision model produced no caption; no caption will be invented')
        rows.append(dict(id='video:' + chunk.parent.name + ':' + str(index), caption=caption,
                         line=int(line), station=int(station), source=str(Path(path).relative_to(ROOT)),
                         chunk=str(chunk.relative_to(ROOT)), offset_seconds=index * 10, duration_seconds=duration,
                         timestamp=(start + dt.timedelta(seconds=index*10)).isoformat(),
                         end_timestamp=(start + dt.timedelta(seconds=index*10+duration)).isoformat(),
                         model=MODELS['vision']['repo']))
    vectors = await embeddings([row['caption'] for row in rows])
    db = lancedb.connect(str(ROOT / 'data/index'))
    data = [dict(row, vector=vector) for row, vector in zip(rows, vectors)]
    # Idempotence: replace only this source's old chunks, preserving other cameras.
    try:
        table = db.open_table('videos')
    except Exception:
        db.create_table('videos', data=data)
    else:
        source = data[0]['source'].replace("'", "''")
        table.delete("source = '" + source + "'")
        table.add(data)
    return len(rows)


async def search_video(query, line=3, station=40, time_range=None):
    vector = (await embeddings(['Instruct: Retrieve relevant visual manufacturing observations.\nQuery: ' + query]))[0]
    table = lancedb.connect(str(ROOT / 'data/index')).open_table('videos')
    where = f'line = {int(line)} AND station = {int(station)}'
    if time_range:
        start = dt.datetime.fromisoformat(time_range['start']).isoformat()
        end = dt.datetime.fromisoformat(time_range['end']).isoformat()
        where += " AND timestamp < '" + end + "' AND end_timestamp > '" + start + "'"
    hits = table.search(vector).where(where).limit(4).to_list()
    clips = [{k: value for k, value in row.items() if k not in ('vector', '_distance')} for row in hits]
    if clips:
        first = clips[0]
        response, measured = await complete('vision', [{'role': 'user', 'content': [
            {'type': 'video_url', 'video_url': {'url': 'file://' + container_path(ROOT / first['chunk'])}},
            {'type': 'text', 'text': 'Check this retrieved clip against the question without assuming its hypothesis is true: ' + query +
             '\nReturn JSON with observation, uncertainty, and flagged_second. Use at most 70 words. '
             'flagged_second is the first visible relevant deviation, in seconds within this clip, or null if none is identifiable. '
             'Do not infer force, calibration or operator identity. Distinguish animation from real footage.'}]}],
            max_tokens=600, extra_body={
                'chat_template_kwargs': {'enable_thinking': False},
                'mm_processor_kwargs': {'fps': 2, 'size': {'shortest_edge': 131072, 'longest_edge': 262144}},
                'structured_outputs': {'json': {'type': 'object', 'properties': {
                    'observation': {'type': 'string'}, 'uncertainty': {'type': 'string'},
                    'flagged_second': {'type': ['number', 'null'], 'minimum': 0, 'maximum': 10}},
                    'required': ['observation', 'uncertainty', 'flagged_second'], 'additionalProperties': False}}})
        first['indexed_caption'] = first['caption']
        verified = json_content(response)
        first['caption'] = verified['observation'] + ' ' + verified['uncertainty']
        if not first['caption']:
            raise ValueError('Live vision verification returned no observable evidence')
        second = verified['flagged_second']
        if second is not None and (isinstance(second, bool) or not isinstance(second, (int, float)) or not 0 <= second < first.get('duration_seconds', 10)):
            raise ValueError('Vision returned an invalid within-clip timestamp')
        first['flagged_second'] = second
        first['seek_seconds'] = first['offset_seconds'] + (second if second is not None else 0)
        first['flagged_timestamp'] = (dt.datetime.fromisoformat(first['timestamp']) + dt.timedelta(seconds=second)).isoformat() if second is not None else None
        first['live_measurement'] = measured
    return {'mode': 'VLM captions + vector search + live top-clip vision verification', 'clips': clips}
