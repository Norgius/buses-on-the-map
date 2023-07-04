import json
from random import randint
from itertools import cycle, islice

import trio
from sys import stderr

from trio_websocket import open_websocket_url

from load_routes import load_routes


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(send_channel, bus_id, route):

    def prepare_bus_data(coords):
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
        await trio.sleep(1)
    for coords in cycle(route['coordinates']):
        bus_data = prepare_bus_data(coords)
        await send_channel.send(bus_data)
        await trio.sleep(1)


async def send_updates(server_address, receive_channel):
    # print(receive_channel)
    async with open_websocket_url(server_address) as ws:
        async for value in receive_channel:
            # print(value)
            await ws.send_message(json.dumps(value))

        await trio.sleep(1)


async def main():
    server_address = 'ws://127.0.0.1:8080'
    try:
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            for route in load_routes():
                for _ in range(20):
                    bus_index = randint(0, len(route['coordinates']) - 1)
                    bus_id = generate_bus_id(route['name'], bus_index)
                    nursery.start_soon(run_bus, send_channel, bus_id, route)
            nursery.start_soon(send_updates, server_address, receive_channel)

    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)

trio.run(main)
