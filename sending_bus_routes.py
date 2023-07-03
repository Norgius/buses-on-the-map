import json

import trio
from sys import stderr
from trio_websocket import open_websocket_url

from load_routes import load_routes


async def run_bus(url, bus_id, route):
    async with open_websocket_url(url) as ws:
        while True:
            for coords in route['coordinates']:
                bus_data = {
                    "busId": f'{bus_id}-0',
                    "lat": coords[0],
                    "lng": coords[1],
                    "route": bus_id
                }
                await ws.send_message(json.dumps(bus_data))
                await trio.sleep(1)


async def main():
    url = 'ws://127.0.0.1:8080'
    try:
        async with trio.open_nursery() as nursery:
            for route in load_routes():
                nursery.start_soon(run_bus, url, route.get('name'), route)

    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)

trio.run(main)
