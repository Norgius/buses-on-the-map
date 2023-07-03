import json
from itertools import cycle

import trio
from sys import stderr
from trio_websocket import open_websocket_url


async def main():
    with open('bus_156.json', 'r',) as f:
        coords = json.load(f)['coordinates']
    try:
        
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            for coord in cycle(coords):
                bus_data = {
                    "busId": "c790сс",
                    "lat": coord[0],
                    "lng": coord[1],
                    "route": "156"
                }
                await ws.send_message(json.dumps(bus_data))
                await trio.sleep(1)
            # message = await ws.get_message()
            # print('Received message: %s' % message)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)

trio.run(main)