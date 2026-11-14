import asyncio
import io
import json
import os
import re
import socket
import struct
import time
from pathlib import Path

import httpx
import qrcode
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from . import telemetry
from . import automotive
from .agent import draft_report, investigate
from .mes import query_mes
from .settings import DB, HERO, MANIFEST, MODELS, PRESETS, ROOT, APP_PORT, installation_mode

app = FastAPI(title='Plant 7: Inside the Line', docs_url=None, redoc_url=None)


@app.middleware('http')
async def local_asset_policy(request, call_next):
    # Original mutating routes retain paths, with presenter authorization for controls.
    if request.method == 'POST' and (request.url.path in ('/api/loadtest','/api/demo-counter/start') or request.url.path.startswith('/api/report/')):
        from .inside_line import TOKEN
        import hmac
        if not hmac.compare_digest(request.headers.get('X-Presenter-Key',''), TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Presenter credential required'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self'; connect-src 'self'; object-src 'none'"
    return response

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
app.mount('/media', StaticFiles(directory=ROOT / 'data/video'), name='media')
SESSION_LIMIT = asyncio.Semaphore(24)
PENDING_LEGACY = 0
TELEMETRY_CACHE = {'at': 0, 'value': None}
TELEMETRY_LOCK = asyncio.Lock()


class Ask(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    replay: bool = False


@app.get('/legacy')
async def index():
    return FileResponse(ROOT / 'static/index.html')


@app.get('/api/config')
async def config():
    return {'hero': HERO, 'presets': PRESETS, 'models': MODELS,
            'public_url': public_url(), 'replay_available': (ROOT / 'runs/golden_run.json').exists(),
            'value': yaml.safe_load((ROOT / 'config/value.yaml').read_text()),
            'notice': 'Procedural footage. Replace with mock station footage before any live show.'}


def public_url():
    supplied = os.environ.get('P7_PUBLIC_URL')
    if supplied:
        return supplied.rstrip('/')
    shared = ROOT / 'runtime/public_url.txt'
    if shared.exists():
        return shared.read_text().strip().rstrip('/')
    try:
        import fcntl
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            address = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack('256s', telemetry.INTERFACE.encode()[:15]))
        host = socket.inet_ntoa(address[20:24])
    except Exception:
        host = '127.0.0.1'
    return 'http://' + host + ':' + str(APP_PORT)


@app.get('/api/qr.svg')
async def qr():
    from qrcode.image.svg import SvgPathImage
    image = qrcode.make(public_url() + '/m', image_factory=SvgPathImage, border=2)
    stream = io.BytesIO()
    image.save(stream)
    return Response(stream.getvalue(), media_type='image/svg+xml')


@app.get('/api/telemetry')
async def live_telemetry():
    async with TELEMETRY_LOCK:
        if time.monotonic()-TELEMETRY_CACHE['at'] > .8:
            TELEMETRY_CACHE.update(value=await telemetry.snapshot(), at=time.monotonic())
        return TELEMETRY_CACHE['value']


@app.post('/api/demo-counter/start')
async def start_demo_counter():
    from .audit import log
    result = telemetry.reset_demo_counter()
    TELEMETRY_CACHE['at'] = 0
    log('Explicit demo interface counter reset ' + json.dumps(result))
    return result


@app.get('/api/health')
async def api_health():
    result = await live_telemetry()
    healthy = all(item['healthy'] for item in result['models'])
    video_index = (ROOT / 'data/index/videos.lance').exists()
    docs_index = (ROOT / 'data/index/documents.lance').exists()
    required = {'brain', 'worker', 'embed', 'rerank'}
    live_ready = required.issubset({m['role'] for m in result['models'] if m['healthy']}) and installation_mode() != 'replay'
    presentation_ready = all(path.exists() for path in [DB, ROOT / 'static/inside/app.js', ROOT / 'data/maintenance_log.csv', ROOT / 'data/shift_notes.md'])
    replay_ready = (ROOT / 'runs/inside-replay.json').exists()
    return {'app': True, 'ready': healthy and DB.exists() and video_index and docs_index,
            'installation_mode': installation_mode(), 'working_slice_ready': presentation_ready and (live_ready if installation_mode() == 'live' else replay_ready),
            'models_ready': healthy, 'models': result['models'], 'database': DB.exists(),
            'documents_index': docs_index, 'video_index': video_index,
            'golden_run': (ROOT / 'runs/golden_run.json').exists(),
            'presentation_ready': presentation_ready,
            'telemetry_investigation_ready': live_ready,
            'vision_ready': next((m['healthy'] for m in result['models'] if m['role']=='vision'),False),
            'synthetic_clip': (ROOT / 'data/video/inside-line.mp4').exists(),
            'captured_local_replay': (ROOT / 'runs/inside-replay.json').exists(),
            'limitations': ['Vision sequence accuracy is unvalidated.','Synthetic demonstration only.','Full multimodal acceptance requires the unavailable vision endpoint.']}


@app.get('/health', response_class=HTMLResponse)
async def health_page():
    return '''<!doctype html><html><head><title>Plant 7 health</title><link rel="stylesheet" href="/static/style.css"></head>
    <body class="health"><h1>Endpoint health</h1><a href="/">Back to investigation</a><div id="checks"></div>
    <script src="/static/health.js"></script></body></html>'''


async def live_events(question):
    async with SESSION_LIMIT:
        telemetry.ACTIVE_SESSIONS += 1
        try:
            async for event in investigate(question):
                yield event
        finally:
            telemetry.ACTIVE_SESSIONS -= 1


async def replay_events():
    path = ROOT / 'runs/golden_run.json'
    if not path.exists():
        raise HTTPException(409, 'No accepted real golden run exists; replay is unavailable')
    trace = json.loads(path.read_text())
    previous = 0
    for original in trace['events']:
        event = dict(original, replay=True)
        await asyncio.sleep(max(0, event.get('elapsed_s', 0)-previous))
        previous = event.get('elapsed_s', previous)
        yield event


@app.post('/api/investigate')
async def ask(request: Ask, http_request: Request):
    global PENDING_LEGACY
    if not request.replay and installation_mode() == 'replay':
        raise HTTPException(503, 'This installation runs the recorded walkthrough. Install live mode to enable local inference.')
    from .inside_line import limit
    limit(http_request, 'legacy-investigations', 24)
    if PENDING_LEGACY >= 24:
        raise HTTPException(429, 'Bounded investigation queue is full')
    if request.replay and not (ROOT / 'runs/golden_run.json').exists():
        raise HTTPException(409, 'No accepted golden run is available')
    PENDING_LEGACY += 1
    async def stream():
        global PENDING_LEGACY
        try:
            events = replay_events() if request.replay else live_events(request.question)
            async for item in events:
                yield 'data: ' + json.dumps(item, default=str) + '\n\n'
        finally:
            PENDING_LEGACY -= 1
    return StreamingResponse(stream(), media_type='text/event-stream',
              headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.get('/api/charts')
async def charts():
    fpy_sql = "SELECT production_date,line,shift,fpy_pct FROM first_pass_yield WHERE line=3 ORDER BY production_date,shift"
    torque_sql = """SELECT u.production_date,t.tool_id,round(avg(t.angle_deg),2) AS angle_deg,
                  round(avg(t.actual_nm),2) AS torque_nm FROM torque_results t JOIN units u USING(unit_id)
                  WHERE t.line=3 GROUP BY u.production_date,t.tool_id ORDER BY u.production_date,t.tool_id"""
    fpy, torque = await asyncio.gather(asyncio.to_thread(query_mes, fpy_sql), asyncio.to_thread(query_mes, torque_sql))
    return {'fpy': fpy['rows'], 'torque': torque['rows'], 'source': 'Synthetic MES SELECT results'}


@app.get('/api/units')
async def units(date: str, shift: int | None = None, tool_id: str | None = None):
    import datetime
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(400, 'Invalid production date')
    if shift is not None and shift not in (1, 2, 3):
        raise HTTPException(400, 'Invalid shift')
    if tool_id is not None and tool_id not in ('T40-A', 'T40-B'):
        raise HTTPException(400, 'Choose a Line 3 Station 40 tool')
    # A daily tool mean covers all shifts. Keep the unit drilldown at that same grain.
    sql = f"SELECT DISTINCT u.unit_id,u.status,u.first_pass,u.supplier_lot FROM units u"
    if tool_id:
        sql += ' JOIN torque_results t USING(unit_id)'
    sql += f" WHERE u.line=3 AND u.production_date=DATE '{day}'"
    if shift is not None:
        sql += f' AND u.shift={shift}'
    if tool_id:
        sql += f" AND t.line=3 AND t.station=40 AND t.tool_id='{tool_id}'"
    sql += ' ORDER BY u.unit_id'
    return await asyncio.to_thread(query_mes, sql)


@app.get('/api/automotive/context')
async def automotive_context(date: str, shift: int | None = None, tool_id: str | None = None):
    try:
        return await asyncio.to_thread(automotive.context, date, shift, tool_id)
    except ValueError as error:
        raise HTTPException(400, str(error))


@app.get('/api/automotive/unit/{unit_id}')
async def automotive_unit(unit_id: str):
    try:
        passport = await asyncio.to_thread(automotive.unit_passport, unit_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if passport is None:
        raise HTTPException(404, 'Synthetic unit not found on Line 3')
    return passport


def read_run(run_id):
    if not re.fullmatch(r'[a-f0-9]{32}', run_id):
        raise HTTPException(404)
    path = ROOT / 'runs' / (run_id + '.json')
    if not path.exists():
        raise HTTPException(404)
    return json.loads(path.read_text())


@app.get('/api/evidence/{run_id}/{evidence_id}')
async def inspect_evidence(run_id: str, evidence_id: str):
    trace = read_run(run_id)
    if evidence_id not in trace['evidence']:
        raise HTTPException(404)
    return trace['evidence'][evidence_id]


@app.post('/api/report/{run_id}')
async def report(run_id: str):
    trace = read_run(run_id)
    answers = [item for item in trace['events'] if item['type'] == 'answer']
    if not answers or not answers[-1].get('complete_sources'):
        raise HTTPException(409, '8D export requires completed data, video and document evidence; this investigation is incomplete')
    existing = ROOT / 'runs' / (run_id + '.md')
    if existing.exists():
        return {'markdown': existing.read_text(), 'source': 'previously generated report for this real run'}
    result = await draft_report(answers[-1]['text'], trace['evidence'], run_id)
    (ROOT / 'runs' / (run_id + '.md')).write_text(result['markdown'])
    return result


@app.get('/api/report/{run_id}.{format}')
async def export_report(run_id: str, format: str):
    trace = read_run(run_id)
    if not any(item['type'] == 'answer' and item.get('complete_sources') for item in trace['events']):
        raise HTTPException(409, 'Incomplete investigation; report is not accepted for export')
    path = ROOT / 'runs' / (run_id + '.md')
    if not path.exists():
        raise HTTPException(409, 'Generate the report first')
    if format == 'md':
        markdown = path.read_text().replace('](/api/evidence/', '](' + public_url() + '/api/evidence/')
        return Response(markdown, media_type='text/markdown',
                        headers={'Content-Disposition': 'attachment; filename=Plant7-8D.md'})
    if format != 'pdf':
        raise HTTPException(404)
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    pdf.setTitle('Plant 7 Proposed 8D')
    y = 800
    for line in path.read_text().splitlines():
        links = re.findall(r'\]\((/api/evidence/[^)]+)\)', line)
        for row in simpleSplit(line, 'Helvetica', 10, 510) or ['']:
            if y < 45:
                pdf.showPage()
                y = 800
            pdf.setFont('Helvetica', 10)
            pdf.drawString(40, y, row)
            if links:
                pdf.linkURL(public_url() + links[0], (40, y-2, 550, y+12), relative=0)
            y -= 14
    pdf.save()
    return Response(output.getvalue(), media_type='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=Plant7-8D.pdf'})


@app.post('/api/loadtest')
async def loadtest():
    if any(job['running'] for job in telemetry.JOBS.values()):
        raise HTTPException(409, 'A load test is already running')
    # Fail immediately when models are absent; never substitute replay for this route.
    state = await api_health()
    if not state['ready']:
        raise HTTPException(503, 'Load test requires every real model, the database and both evidence indexes ready')
    import uuid
    job_id = uuid.uuid4().hex
    job = telemetry.JOBS[job_id] = {'running': True, 'requested': 20, 'completed': 0, 'failed': 0, 'started_at': time.time()}
    async def run_one(index):
        failed = False
        answered = False
        try:
            async for event in live_events(PRESETS[index % len(PRESETS)]):
                failed = failed or event['type'] == 'error'
                answered = answered or event['type'] == 'answer'
        except Exception:
            failed = True
        failed = failed or not answered
        job['failed' if failed else 'completed'] += 1
    async def execute():
        try:
            await asyncio.gather(*(run_one(index) for index in range(20)))
        finally:
            job.update(running=False, elapsed_s=time.time()-job['started_at'])
    task = asyncio.create_task(execute())
    # Keep a strong reference for the background task lifetime.
    app.state.load_task = task
    return {'job_id': job_id, **job}


# Shared local presentation routes; existing inference and source APIs are preserved.
from .inside_line import router as inside_router
app.include_router(inside_router)

@app.get('/')
@app.get('/wall')
@app.get('/compute')
@app.get('/m')
async def inside_page():
    return FileResponse(ROOT / 'static/inside/index.html')
