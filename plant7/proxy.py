"""Loopback TCP to local Unix sockets. Inference containers have no network."""
import asyncio
from .settings import MODELS, ROOT


async def forward(reader, writer, role):
    upstream = None
    try:
        initial = b''
        if role == 'embed':
            initial = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 10)
            target = initial.split(b' ', 2)[1].split(b'?', 1)[0]
            if target in (b'/rerank', b'/v1/rerank', b'/score', b'/v1/score'):
                role = 'rerank'
            # One HTTP request per connection lets this gateway route pooling tasks correctly.
            lines = initial[:-4].split(b'\r\n')
            lines = [line for line in lines if not line.lower().startswith(b'connection:')]
            initial = b'\r\n'.join(lines) + b'\r\nConnection: close\r\n\r\n'
        upstream_reader, upstream = await asyncio.open_unix_connection(str(ROOT / 'runtime/sockets' / role / 'model.sock'))
        if initial:
            upstream.write(initial)
            await upstream.drain()
        async def copy(source, destination):
            while data := await source.read(65536):
                destination.write(data)
                await destination.drain()
            if destination.can_write_eof():
                destination.write_eof()
        await asyncio.gather(copy(reader, upstream), copy(upstream_reader, writer))
    except (OSError, ConnectionError, TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        pass
    finally:
        writer.close()
        if upstream:
            upstream.close()


async def main():
    roles = dict(MODELS)
    roles['challenger_worker'] = {'port': 8013}
    servers = []
    for role, model in roles.items():
        server = await asyncio.start_server(lambda r, w, role=role: forward(r, w, role), '127.0.0.1', model['port'])
        servers.append(server)
    await asyncio.gather(*(server.serve_forever() for server in servers))


if __name__ == '__main__':
    asyncio.run(main())
