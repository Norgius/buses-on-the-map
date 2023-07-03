import json

import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            print(json.loads(message))
            # await ws.send_message(json.dumps(some_buses))
        except ConnectionClosed:
            break


async def main():
    await serve_websocket(echo_server, '127.0.0.1', 8080, ssl_context=None)

trio.run(main)