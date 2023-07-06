import json
import logging
from typing import Union
from dataclasses import dataclass, asdict
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__name__)


@dataclass
class Bus:
    msgType: str = 'Buses'
    buses: list = None


@dataclass
class WindowBounds:
    south_lat: Union[float, None] = None
    north_lat: Union[float, None] = None
    west_lng: Union[float, None] = None
    east_lng: Union[float, None] = None

    def is_inside(self, lat, lng):
        if self.south_lat is None:
            return
        if self.south_lat < lat < self.north_lat and \
                self.west_lng < lng < self.east_lng:
            return True


bounds = WindowBounds()
buses_on_screen = Bus(buses=[])


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
            if bounds.is_inside(bus_data['lat'], bus_data['lng']):
                buses_on_screen.buses.append(bus_data)
        except ConnectionClosed:
            logger.warning('Lost connection with client')
            break


async def listen_browser(ws):
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            global bounds
            bounds = WindowBounds(*message.get('data').values())
            logger.debug(message)
        except ConnectionClosed:
            logger.warning('Browser page closed')
            break


async def send_buses(ws):
    while True:
        try:
            global bounds
            global buses_on_screen
            past_bounds = bounds
            await trio.sleep(1)
            await ws.send_message(
                json.dumps(asdict(buses_on_screen), ensure_ascii=False)
            )
            if past_bounds != bounds:
                logger.debug(f'{len(buses_on_screen.buses)} buses inside bounds')
            buses_on_screen.buses = []
        except ConnectionClosed:
            buses_on_screen.buses = []
            bounds = WindowBounds()
            logger.warning('Browser page closed')
            break


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
