import json
import logging
from typing import Union
from dataclasses import dataclass, asdict
from contextlib import suppress
from functools import partial

import asyncclick as click
import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__name__)
buses = {}


class InvalidJSON(Exception):
    pass


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


def validate_browser_message(message):
    try:
        message = json.loads(message)
        if message.get('msgType') is None and message.get('msgType') != 'newBounds':
            raise InvalidJSON
        if not message.get('data') or not isinstance(message.get('data'), dict):
            raise InvalidJSON

        coords_in_message = message.get('data')
        valid_coords = {
            'south_lat': (-90, 90),
            'north_lat': (-90, 90),
            'west_lng': (-180, 180),
            'east_lng': (-180, 180)
        }
        for direction, valid_coords in valid_coords.items():
            coord_in_message = coords_in_message.get(direction)
            if coord_in_message is None or \
                    not isinstance(coord_in_message, (float, int)):
                raise InvalidJSON

            elif not valid_coords[0] <= coord_in_message <= valid_coords[1]:
                raise InvalidJSON
        return message

    except json.JSONDecodeError:
        logger.warning('JSONDecodeError')
        return {'errors': ['Requires valid JSON'], 'msgType': 'Errors'}
    except InvalidJSON:
        logger.warning('InvalidJSON')
        return {'errors': ['Requires msgType specified'], 'msgType': 'Errors'}


async def listen_browser(ws, bounds):
    while True:
        try:
            message = await ws.get_message()
            message = validate_browser_message(message)
            if 'errors' in message:
                await ws.send_message(json.dumps(message, ensure_ascii=False))
                continue
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


@click.command()
@click.option('-b', '--bus_port', default=8080, help='Адрес сервера клиента')
@click.option('-br', '--browser_port', default=8000, help='Адрес сервера браузера')
@click.option('-l', '--log', is_flag=True, default=False, help='Настройка логирования')
async def main(bus_port, browser_port, log):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)
    logger.disabled = not log

    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                receiving_server,
                '127.0.0.1',
                bus_port,
                ssl_context=None
            )
        )
        nursery.start_soon(
            partial(
                serve_websocket,
                server_for_browser,
                '127.0.0.1',
                browser_port,
                ssl_context=None
            )
        )
        logger.info('Server started')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
