"""BM25 + dense reciprocal rank fusion, followed by the local reranker."""
import re
import hashlib
import json
from pathlib import Path

import lancedb
import numpy as np
from rank_bm25 import BM25Okapi

from .clients import embeddings, rerank
from .settings import MODELS, ROOT, source_paths


def corpus_signature():
    digest = hashlib.sha256()
    for path in source_paths():
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes())
    return digest.hexdigest()


def passages():
    rows = []
    for path in source_paths():
        text = path.read_text()
        lines = text.splitlines()
        for start in range(0, len(lines), 6):
            rows.append({'id': str(path.relative_to(ROOT)) + ':' + str(start+1),
                         'doc_id': str(path.relative_to(ROOT)), 'line': start+1,
                         'text': '\n'.join(lines[max(0, start-1):start+7])})
    return rows


def tokenize(text):
    return re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text.lower())


async def build_docs_index():
    signature = corpus_signature()
    rows = passages()
    vectors = await embeddings([row['text'] for row in rows])
    if corpus_signature() != signature:
        raise RuntimeError('Controlled sources changed during indexing; rebuild the index')
    data = [dict(row, vector=vector) for row, vector in zip(rows, vectors)]
    db = lancedb.connect(str(ROOT / 'data/index'))
    db.create_table('documents', data=data, mode='overwrite')
    (ROOT / 'data/index/documents_manifest.json').write_text(json.dumps({
        'signature': signature, 'model': MODELS['embed']['repo'], 'revision': MODELS['embed']['revision']}))
    return len(data)


async def search_docs(query):
    rows = passages()
    bm25 = BM25Okapi([tokenize(row['text']) for row in rows])
    lexical = list(np.argsort(bm25.get_scores(tokenize(query)))[::-1][:12])
    ranking = {rows[i]['id']: 1/(60+rank) for rank, i in enumerate(lexical, 1)}
    pool = {rows[i]['id']: rows[i] for i in lexical}
    status = 'BM25 only; dense index or endpoint unavailable'
    try:
        manifest = json.loads((ROOT / 'data/index/documents_manifest.json').read_text())
        if manifest != {'signature': corpus_signature(), 'model': MODELS['embed']['repo'], 'revision': MODELS['embed']['revision']}:
            raise ValueError('Dense index is stale; rebuild before claiming hybrid retrieval')
        db = lancedb.connect(str(ROOT / 'data/index'))
        vector = (await embeddings(['Instruct: Retrieve manufacturing evidence for this question.\nQuery: ' + query]))[0]
        dense = db.open_table('documents').search(vector).limit(12).to_list()
        for rank, row in enumerate(dense, 1):
            pool[row['id']] = {k: row[k] for k in ['id', 'doc_id', 'line', 'text']}
            ranking[row['id']] = ranking.get(row['id'], 0) + 1/(60+rank)
        status = 'BM25 + embeddings; reranker unavailable'
    except (Exception,) as error:
        dense_error = str(error)[:180]
    candidates = [pool[key] for key in sorted(ranking, key=ranking.get, reverse=True)[:12]]
    try:
        scores = await rerank(query, [row['text'] for row in candidates])
        candidates = [dict(candidates[item['index']], rerank_score=item.get('relevance_score')) for item in scores]
        if status.startswith('BM25 +'):
            status = 'BM25 + embeddings + rerank'
        else:
            status = 'BM25 + rerank; dense retrieval unavailable'
    except Exception:
        pass
    return {'mode': status, 'dense_error': locals().get('dense_error'), 'passages': candidates[:6]}


def long_context_documents(doc_ids):
    allowed = {str(path.relative_to(ROOT)): path for path in source_paths()}
    if not doc_ids or len(doc_ids) > 16 or any(key not in allowed for key in doc_ids):
        raise ValueError('Choose 1 to 16 known source document IDs')
    documents = [{'id': key, 'text': allowed[key].read_text()} for key in doc_ids]
    if sum(len(row['text']) for row in documents) > 300000:
        raise ValueError('Document selection exceeds conservative context character limit')
    return documents
