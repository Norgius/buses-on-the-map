import json
import logging

import trio
from trio_websocket import open_websocket_url

logger = logging.getLogger('test_data_of_bus')
errors = [
    {'errors': ['Requires type JSON'], 'msgType': 'Errors'},
    {'errors': ['Requires valid route'], 'msgType': 'Errors'},
    {'errors': ['Requires valid coords'], 'msgType': 'Errors'},
    {'errors': ['Requires busId specified'], 'msgType': 'Errors'}
]


async def test_client():
    try:
        async with open_websocket_url('ws://127.0.0.1:8080', connect_timeout=5) as ws:

            await ws.send_message('hello world!')
            response = await ws.get_message()
            if json.loads(response) == errors[0]:
                logger.info('1-ая проверка пройдена')

            await ws.send_message(json.dumps({'some_data': '111newBounds'}))
            response = await ws.get_message()
            if json.loads(response) == errors[3]:
                logger.info('2-ая проверка пройдена')

            invalid_message = {
                    "busId": '76e-26',
                    "lat": 39.23623531,
                    "route": '76e'
                }
            await ws.send_message(json.dumps(invalid_message))
            response = await ws.get_message()
            if json.loads(response) == errors[2]:
                logger.info('3-ая проверка пройдена')

            invalid_message = {
                    "busId": '76e-26',
                    "lat": 55.860268253711,
                    "lng": 37.602014843876,
                    "route": (1251, 'awffgw')
                }
            await ws.send_message(json.dumps(invalid_message))
            response = await ws.get_message()
            if json.loads(response) == errors[1]:
                logger.info('4-ая проверка пройдена')

            valid_message = {
                    "busId": '76e-26',
                    "lat": 55.860268253711,
                    "lng": 37.602014843876,
                    "route": '76e'
                }
            with trio.fail_after(5):
                await ws.send_message(json.dumps(valid_message))
                response = await ws.get_message()

    except OSError as ose:
        logger.error('Connection attempt failed: %s', ose)
    except trio.TooSlowError:
        logger.info('5-ая проверка пройдена')

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)
    trio.run(test_client)
