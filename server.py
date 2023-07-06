import json
import logging
from typing import Union
from dataclasses import dataclass, asdict
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__name__)
buses = {}


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


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

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


async def server_for_browser(request):
    ws = await request.accept()
    bounds = WindowBounds()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(send_buses, ws, bounds)


async def receiving_server(request):
    ws = await request.accept()
    while True:
        try:
            raw_data = await ws.get_message()
            bus_data = json.loads(raw_data)
            bus = Bus(**bus_data)
            buses[bus.busId] = bus
        except ConnectionClosed:
            logger.warning('Lost connection with client')
            break


async def listen_browser(ws, bounds):
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            bounds.update(*message.get('data').values())
            logger.debug(message)
        except ConnectionClosed:
            break


async def send_buses(ws, bounds):
    while True:
        try:
            buses_on_screen = [
                asdict(bus) for bus in buses.values()
                if bounds.is_inside(bus.lat, bus.lng)
            ]

            past_bounds = bounds
            await trio.sleep(1)
            await ws.send_message(json.dumps(
                {'msgType': 'Buses', 'buses': buses_on_screen},
                ensure_ascii=False
            ))

            if past_bounds != bounds:
                logger.debug(f'{len(buses_on_screen.buses)} buses inside bounds')
        except ConnectionClosed:
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
