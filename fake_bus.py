import json
import logging
from functools import wraps
from contextlib import suppress
from sys import stderr
from random import randint, choice
from itertools import cycle, islice

import trio
import asyncclick as click
from trio import MemoryReceiveChannel, MemorySendChannel
from trio_websocket import open_websocket_url, ConnectionClosed, HandshakeError

from load_routes import load_routes

logger = logging.getLogger(__name__)


def generate_bus_id(route_id: str, bus_index: str, emulator_id: str) -> str:
    bus_id = f"{route_id}-{bus_index}"
    if emulator_id:
        bus_id = f'{emulator_id}_{bus_id}'
    return bus_id


async def run_bus(send_channel: MemorySendChannel,
                  bus_id: str,
                  route: dict,
                  refresh_timeout: float):

    def prepare_bus_data(coords: tuple) -> dict:
        bus_data = {
                    "busId": bus_id,
                    "lat": coords[0],
                    "lng": coords[1],
                    "route": route['name']
                }
        return bus_data

    for coords in islice(route['coordinates'], int(bus_id.split('-')[1]), None):
        bus_data = prepare_bus_data(coords)
        await send_channel.send(bus_data)
        await trio.sleep(refresh_timeout)
    for coords in cycle(route['coordinates']):
        bus_data = prepare_bus_data(coords)
        await send_channel.send(bus_data)
        await trio.sleep(refresh_timeout)


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await async_function(*args, **kwargs)
            except HandshakeError:
                logger.warning('Server is down')
                await trio.sleep(5)
            except ConnectionClosed:
                logger.warning('Lost connection with server')
                await trio.sleep(5)
    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address: str,
                       receive_channel: MemoryReceiveChannel):
    async with open_websocket_url(server_address) as ws:

        async for value in receive_channel:
            await ws.send_message(json.dumps(value))


@click.command()
@click.option('-s', '--server_address', default='ws://127.0.0.1:8080', help='Адрес сервера')
@click.option('-r', '--routes_number', default=500, help='Кол-во маршрутов')
@click.option('-b', '--buses_per_route', default=3, help='Кол-во автобусов на каждом маршруте')
@click.option('-w', '--websockets_number', default=1, help='Кол-во открытых веб-сокетов')
@click.option('-e', '--emulator_id', default='', help='Префикс к busId')
@click.option('-t', '--refresh_timeout', default=1.0, help='Задержка в обновлении координат')
@click.option('-l', '--log', is_flag=True, default=False, help='Настройка логирования')
async def main(server_address: str,
               routes_number: int,
               buses_per_route: int,
               websockets_number: int,
               emulator_id: str,
               refresh_timeout: float,
               log: bool):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    logger.disabled = not log
    logger.info('Start')
    while True:
        try:
            send_channels, receive_channels = [], []
            for _ in range(websockets_number):
                send_channel, receive_channel = trio.open_memory_channel(5)
                receive_channels.append(receive_channel)
                send_channels.append(send_channel)

            async with trio.open_nursery() as nursery:
                for num, route in enumerate(load_routes(), 0):
                    if num >= routes_number:
                        break
                    for _ in range(buses_per_route):
                        bus_index = randint(0, len(route['coordinates']) - 1)
                        bus_id = generate_bus_id(route['name'], bus_index, emulator_id)
                        nursery.start_soon(
                            run_bus, choice(send_channels), bus_id, route, refresh_timeout
                        )
                for receive_channel in receive_channels:
                    nursery.start_soon(send_updates, server_address, receive_channel)

        except OSError as ose:
            logger.warning('Connection attempt failed: %s' % ose, file=stderr)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
