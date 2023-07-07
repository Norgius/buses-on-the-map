import json
import logging

import trio
from trio_websocket import open_websocket_url

errors = [
    {'errors': ['Requires valid JSON'], 'msgType': 'Errors'},
    {'errors': ['Requires msgType specified'], 'msgType': 'Errors'}
]


async def test_client():
    try:
        async with open_websocket_url('ws://127.0.0.1:8000') as ws:

            await ws.send_message('hello world!')
            response = await ws.get_message()
            if json.loads(response) == errors[0]:
                print('1-ая проверка пройдена')

            await ws.send_message(json.dumps({'some_data': '111newBounds'}))
            response = await ws.get_message()
            if json.loads(response) == errors[1]:
                print('2-ая проверка пройдена')

            invalid_message = {
                'msgType': 'newBounds',
                'data':
                    {'south_lat': 30,
                     'north_lat': 'awd',
                     'west_lng': 37.37,
                     'east_lng': 37.5387
                     }
            }
            await ws.send_message(json.dumps(invalid_message))
            response = await ws.get_message()
            if json.loads(response) == errors[1]:
                print('3-ая проверка пройдена')

            invalid_message = {
                'msgType': 'newBounds',
                'data': ['awdawd', 'safgsg']
            }
            await ws.send_message(json.dumps(invalid_message))
            response = await ws.get_message()
            if json.loads(response) == errors[1]:
                print('4-ая проверка пройдена')

            valid_message = {
                'msgType': 'newBounds',
                'data':
                    {'south_lat': 55.79790385560228,
                     'north_lat': 55.84260277600231,
                     'west_lng': 37.3751449584961,
                     'east_lng': 37.5399398803711
                     }
            }
            await ws.send_message(json.dumps(valid_message))
            response = await ws.get_message()
            if 'errors' not in json.loads(response):
                print('5-ая проверка пройдена')

    except OSError as ose:
        logging.error('Connection attempt failed: %s', ose)


trio.run(test_client)
