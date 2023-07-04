import json
import logging
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__name__)

buses = {'msgType': 'Buses', 'buses': []}


async def receiving_server(request):
    ws = await request.accept()
    while True:
        try:
            raw_data = await ws.get_message()
            bus_data = json.loads(raw_data)
            buses['buses'].append(bus_data)
            logger.info(
                f'Place new bus #{bus_data["lat"]:.3f}-{bus_data["lng"]:.3f} on the map.'
                f' Route {bus_data["route"]}'
            )
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    ws = await request.accept()
    while True:
        try:
            await trio.sleep(1)
            await ws.send_message(json.dumps(buses, ensure_ascii=False))
            buses['buses'] = []
        except ConnectionClosed:
            break


async def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(partial(serve_websocket, receiving_server, '127.0.0.1', 8080, ssl_context=None))
        nursery.start_soon(partial(serve_websocket, talk_to_browser, '127.0.0.1', 8000, ssl_context=None))

trio.run(main)
