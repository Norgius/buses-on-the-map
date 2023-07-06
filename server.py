import json
import logging
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__name__)

bounds = None
buses = {'msgType': 'Buses', 'buses': []}


def is_inside(bounds, lat, lng):
    if not bounds:
        return
    if bounds['south_lat'] < lat < bounds['north_lat'] and \
            bounds['west_lng'] < lng < bounds['east_lng']:
        return True


async def server_for_browser(request):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws)
        nursery.start_soon(send_buses, ws)


async def receiving_server(request):
    ws = await request.accept()
    while True:
        try:
            raw_data = await ws.get_message()
            bus_data = json.loads(raw_data)
            if is_inside(bounds, bus_data['lat'], bus_data['lng']):
                buses['buses'].append(bus_data)
            # logger.info(
            #     f'Place new bus #{bus_data["lat"]:.3f}-{bus_data["lng"]:.3f} on the map.'
            #     f' Route {bus_data["route"]}'
            # )
        except ConnectionClosed:
            logger.warning('Lost connection with client')
            break


async def listen_browser(ws):
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            global bounds
            bounds = message.get('data')
            logger.debug(message)
        except ConnectionClosed:
            logger.warning('Browser page closed')
            break


async def send_buses(ws):
    while True:
        try:
            past_bounds = bounds
            await trio.sleep(1)
            await ws.send_message(json.dumps(buses, ensure_ascii=False))
            if past_bounds != bounds:
                logger.debug(f'{len(buses["buses"])} buses inside bounds')
            buses['buses'] = []
        except ConnectionClosed:
            logger.warning('Browser page closed')
            break


async def send_buses(ws, bounds):
    pass


async def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                receiving_server,
                '127.0.0.1',
                8080,
                ssl_context=None
            )
        )
        nursery.start_soon(
            partial(
                serve_websocket,
                server_for_browser,
                '127.0.0.1',
                8000,
                ssl_context=None
            )
        )
        logger.info('Server started')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
