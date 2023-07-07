import json
import logging

import trio
from trio_websocket import open_websocket_url

logger = logging.getLogger('test_client')
errors = [
    {'errors': ['Requires type JSON'], 'msgType': 'Errors'},
    {'errors': ['Requires valid coords'], 'msgType': 'Errors'},
    {'errors': ['Requires msgType specified'], 'msgType': 'Errors'}
]


async def test_client():
    try:
        async with open_websocket_url('ws://127.0.0.1:8000') as ws:

            await ws.send_message('hello world!')
            response = await ws.get_message()
            if json.loads(response) == errors[0]:
                logger.info('1-ая проверка пройдена')

            await ws.send_message(json.dumps({'some_data': '111newBounds'}))
            response = await ws.get_message()
            if json.loads(response) == errors[2]:
                logger.info('2-ая проверка пройдена')

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
                logger.info('3-ая проверка пройдена')

            invalid_message = {
                'msgType': 'newBounds',
                'data': ['awdawd', 'safgsg']
            }
            await ws.send_message(json.dumps(invalid_message))
            response = await ws.get_message()
            if json.loads(response) == errors[1]:
                logger.info('4-ая проверка пройдена')

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
                logger.info('5-ая проверка пройдена')

    except OSError as ose:
        logger.error('Connection attempt failed: %s', ose)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)
    trio.run(test_client)
