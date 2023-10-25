import json
import logging
from typing import Type
from pydantic_core import PydanticCustomError
from pydantic import BaseModel, Field, ValidationError, field_validator
from contextlib import suppress

import asyncclick as click
import trio
from trio_websocket import (serve_websocket,
                            ConnectionClosed,
                            WebSocketRequest,
                            WebSocketConnection)


logger = logging.getLogger(__name__)
buses = {}


class Bus(BaseModel):
    busId: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    route: str


class WindowBounds(BaseModel):
    south_lat: float = Field(ge=-90, le=90)
    north_lat: float = Field(ge=-90, le=90)
    west_lng: float = Field(ge=-180, le=180)
    east_lng: float = Field(ge=-180, le=180)

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng

    def is_inside(self, bus: Type[Bus]) -> bool:
        if self.south_lat < bus.lat < self.north_lat and \
                self.west_lng < bus.lng < self.east_lng:
            return True


class NewBoundsMessage(BaseModel):
    msgType: str
    data: WindowBounds

    @field_validator('msgType')
    @classmethod
    def validate_msgtype(cls, data):
        if data != 'newBounds':
            raise PydanticCustomError(
                'not is newBounds',
                'value is not "newBounds", got "{wrong_value}"',
                dict(wrong_value=data),
            )
        return data


def check_bus_message(message: str) -> Type[Bus] | dict:
    try:
        bus = Bus.model_validate_json(message)
        return bus
    except ValidationError as err:
        logger.warning('ValidationError')
        return {'errors': [err.errors()], 'msgType': 'Errors'}


async def receiving_server(request: WebSocketRequest):
    ws: WebSocketConnection = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            checked_message: Type[Bus] | dict = check_bus_message(message)
            if 'errors' in checked_message:
                await ws.send_message(json.dumps(checked_message, ensure_ascii=False))
            else:
                buses[checked_message.busId] = checked_message
                await ws.send_message(json.dumps({'msgType': 'Success', 'message': message}))
        except ConnectionClosed:
            logger.warning('Lost connection with bus data')
            break


def check_browser_message(message: str) -> Type[NewBoundsMessage] | dict:
    try:
        new_bounds_message = NewBoundsMessage.model_validate_json(message)
        return new_bounds_message
    except ValidationError as err:
        logger.warning('ValidationError')
        return {'errors': [err.errors()], 'msgType': 'Errors'}


async def listen_browser(ws: WebSocketConnection, bounds: WindowBounds):
    while True:
        try:
            message = await ws.get_message()
            checked_message: Type[NewBoundsMessage] | dict = check_browser_message(message)
            if 'errors' in checked_message:
                await ws.send_message(json.dumps(checked_message, ensure_ascii=False))
            else:
                bounds.update(**checked_message.data.model_dump())
                logger.debug(checked_message)
        except ConnectionClosed:
            break


async def send_buses(ws: WebSocketConnection, bounds: WindowBounds):
    while True:
        try:
            buses_on_screen = [
                dict(bus) for bus in buses.values()
                if bounds.is_inside(bus)
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
    bounds = WindowBounds(
        south_lat=0,
        north_lat=0,
        west_lng=0,
        east_lng=0
    )
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
