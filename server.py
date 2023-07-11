import json
import logging
from typing import Union
from dataclasses import dataclass, asdict
from contextlib import suppress

import asyncclick as click
import trio
from trio_websocket import (serve_websocket,
                            ConnectionClosed,
                            WebSocketRequest,
                            WebSocketConnection)

from custom_exceptions import (InvalidRouteError,
                               MessageTypeError,
                               InvalidCoordsError)

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


def check_bus_message(message: str) -> dict:
    try:
        message = json.loads(message)
        busId = message.get('busId')
        if busId is None or not isinstance(busId, str):
            raise MessageTypeError

        route = message.get('route')
        if route is None or not isinstance(route, str):
            raise InvalidRouteError

        valid_coords = {
            'lat': (-90, 90),
            'lng': (-180, 180),
        }
        for line, valid_coords in valid_coords.items():
            coord_in_message = message.get(line)
            if coord_in_message is None or \
                    not isinstance(coord_in_message, (float, int)):
                raise InvalidCoordsError
            elif not valid_coords[0] <= coord_in_message <= valid_coords[1]:
                raise InvalidCoordsError
        return message

    except json.JSONDecodeError:
        logger.warning('JSONDecodeError')
        return {'errors': ['Requires type JSON'], 'msgType': 'Errors'}
    except InvalidCoordsError:
        logger.warning('InvalidCoordsError')
        return {'errors': ['Requires valid coords'], 'msgType': 'Errors'}
    except InvalidRouteError:
        logger.warning('InvalidRouteError')
        return {'errors': ['Requires valid route'], 'msgType': 'Errors'}
    except MessageTypeError:
        logger.warning('MessageTypeError')
        return {'errors': ['Requires busId specified'], 'msgType': 'Errors'}


async def receiving_server(request: WebSocketRequest):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            message = check_bus_message(message)
            if 'errors' in message:
                await ws.send_message(json.dumps(message, ensure_ascii=False))
                continue
            bus = Bus(**message)
            buses[bus.busId] = bus
        except ConnectionClosed:
            logger.warning('Lost connection with bus data')
            break


def check_browser_message(message: str) -> dict:
    try:
        message = json.loads(message)
        msgType = message.get('msgType')
        if msgType is None or msgType != 'newBounds':
            raise MessageTypeError

        message_data = message.get('data')
        if message_data is None or not isinstance(message_data, dict):
            raise InvalidCoordsError

        coords_in_message = message.get('data')
        valid_coords = {
            'south_lat': (-90, 90),
            'north_lat': (-90, 90),
            'west_lng': (-180, 180),
            'east_lng': (-180, 180),
        }
        for direction, valid_coords in valid_coords.items():
            coord_in_message = coords_in_message.get(direction)
            if coord_in_message is None or \
                    not isinstance(coord_in_message, (float, int)):
                raise InvalidCoordsError
            elif not valid_coords[0] <= coord_in_message <= valid_coords[1]:
                raise InvalidCoordsError
        return message

    except json.JSONDecodeError:
        logger.warning('JSONDecodeError')
        return {'errors': ['Requires type JSON'], 'msgType': 'Errors'}
    except InvalidCoordsError:
        logger.warning('InvalidCoordsError')
        return {'errors': ['Requires valid coords'], 'msgType': 'Errors'}
    except MessageTypeError:
        logger.warning('MessageTypeError')
        return {'errors': ['Requires msgType specified'], 'msgType': 'Errors'}


async def listen_browser(ws: WebSocketConnection, bounds: WindowBounds):
    while True:
        try:
            message = await ws.get_message()
            message = check_browser_message(message)
            if 'errors' in message:
                await ws.send_message(json.dumps(message, ensure_ascii=False))
                continue
            bounds.update(*message.get('data').values())
            logger.debug(message)
        except ConnectionClosed:
            break


async def send_buses(ws: WebSocketConnection, bounds: WindowBounds):
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


async def server_for_browser(request: WebSocketRequest):
    ws = await request.accept()
    bounds = WindowBounds()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(send_buses, ws, bounds)


@click.command()
@click.option('-ba', '--bus_address', default='127.0.0.1', help='Адрес сервера для автобусов')
@click.option('-bra', '--browser_address', default='127.0.0.1', help='Адрес сервера для клиента')
@click.option('-b', '--bus_port', default=8080, help='Порт сервера для автобусов')
@click.option('-br', '--browser_port', default=8000, help='Порт сервера для клиента')
@click.option('-l', '--log', is_flag=True, default=False, help='Настройка логирования')
async def main(bus_address: str,
               browser_address: str,
               bus_port: int,
               browser_port: int,
               log: bool):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)
    logger.disabled = not log

    async with trio.open_nursery() as nursery:
        nursery.start_soon(
                serve_websocket,
                receiving_server,
                bus_address,
                bus_port,
                None
        )
        nursery.start_soon(
                serve_websocket,
                server_for_browser,
                browser_address,
                browser_port,
                None
        )
        logger.info('Server started')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
