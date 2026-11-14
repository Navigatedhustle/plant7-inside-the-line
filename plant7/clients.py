"""OpenAI compatible streaming with server-reported token counts only."""
import json
import time
from collections import deque
from contextvars import ContextVar

import httpx
from openai import AsyncOpenAI

from .settings import MODELS

MEASUREMENTS = deque(maxlen=10000)
RUN_USAGE = ContextVar('plant7_run_usage', default=None)


def record_usage(measured):
    MEASUREMENTS.append(measured)
    sink = RUN_USAGE.get()
    if sink is not None:
        sink.append(measured)


def client(role):
    model = MODELS[role]
    return AsyncOpenAI(base_url=f"http://127.0.0.1:{model['port']}/v1", api_key='local-only',
                       max_retries=0, timeout=75,
                       http_client=httpx.AsyncClient(trust_env=False))


async def complete(role, messages, tools=None, max_tokens=1600, extra_body=None):
    start = time.monotonic()
    first = None
    content, calls, usage, finish_reason = [], {}, None, None
    kwargs = dict(model=MODELS[role]['repo'], messages=messages, temperature=0,
                  max_tokens=max_tokens, stream=True, stream_options={'include_usage': True})
    if role in ('brain', 'worker') and 'Qwen' in MODELS[role]['repo']:
        kwargs['extra_body'] = {'chat_template_kwargs': {'enable_thinking': False}}
    if tools:
        kwargs['tools'] = tools
        kwargs['tool_choice'] = 'auto'
    if extra_body:
        kwargs['extra_body'] = extra_body
    async with client(role) as api:
        stream = await api.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            for choice in chunk.choices:
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                delta = choice.delta
                extras = getattr(delta, 'model_extra', None) or {}
                reasoning_delta = extras.get('reasoning') or extras.get('reasoning_content') or getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                if delta.content or delta.tool_calls or reasoning_delta:
                    if first is None:
                        first = time.monotonic()
                if delta.content:
                    content.append(delta.content)
                for item in delta.tool_calls or []:
                    call = calls.setdefault(item.index, {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                    if item.id:
                        call['id'] = item.id
                    if item.function:
                        if item.function.name:
                            call['function']['name'] += item.function.name
                        if item.function.arguments:
                            call['function']['arguments'] += item.function.arguments
    end = time.monotonic()
    measured = dict(role=role, at=time.time(), elapsed_s=end-start, finish_reason=finish_reason,
                    ttft_s=first-start if first else None,
                    decode_s=end-first if first else None,
                    completion_tokens=usage.completion_tokens if usage else None,
                    prompt_tokens=usage.prompt_tokens if usage else None)
    measured['tokens_per_second'] = (measured['completion_tokens'] / max(end-first, .001)
                                      if usage and first else None)
    record_usage(measured)
    message = {'role': 'assistant', 'content': ''.join(content) or None}
    if calls:
        message['tool_calls'] = [calls[i] for i in sorted(calls)]
    return message, measured


def json_content(message):
    text = message.get('content') or ''
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise ValueError('Model did not return a JSON object')
    return json.loads(text[start:end+1])


async def embeddings(texts):
    started = time.monotonic()
    async with client('embed') as api:
        result = await api.embeddings.create(model=MODELS['embed']['repo'], input=texts)
    record_usage({'role': 'embed', 'elapsed_s': time.monotonic()-started,
                  'prompt_tokens': result.usage.prompt_tokens if result.usage else None,
                  'completion_tokens': 0})
    return [row.embedding for row in sorted(result.data, key=lambda row: row.index)]


async def rerank(query, documents):
    started = time.monotonic()
    async with httpx.AsyncClient(trust_env=False, timeout=30) as api:
        result = await api.post(f"http://127.0.0.1:{MODELS['embed']['port']}/rerank",
                                json={'model': MODELS['rerank']['repo'], 'query': query,
                                      'documents': documents, 'top_n': min(6, len(documents))})
        result.raise_for_status()
        payload = result.json()
        usage = payload.get('usage') or {}
        record_usage({'role': 'rerank', 'elapsed_s': time.monotonic()-started,
                      'prompt_tokens': usage.get('prompt_tokens'), 'completion_tokens': 0})
        return payload['results']
