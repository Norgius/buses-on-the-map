import json

import pytest
from trio_websocket import open_websocket_url


wrong_messages = [
    'hello world',
    {
        'msgType': 'Wrong',
        'data': {
            'south_lat': 55.73078331708113,
            'north_lat': 55.775752368601495,
            'west_lng': 37.36209869384766,
            'east_lng': 37.52689361572266
        }
    },
    {
        'msgType': 'newBounds',
        'data': {
            'south_lat': 55.73078331708113,
            'west_lng': 37.36209869384766,
            'east_lng': 37.52689361572266
        }
    },
    {
        'msgType': 'newBounds',
        'data': {
            'south_lat': 55.73078331708113,
            'north_lat': -100.26213413545,
            'west_lng': 37.36209869384766,
            'east_lng': 37.52689361572266
        }
    },

]

correct_message = [
    {
        'msgType': 'newBounds',
        'data': {
            'south_lat': 55.73078331708113,
            'north_lat': 55.26213413545,
            'west_lng': 37.36209869384766,
            'east_lng': 37.52689361572266
        }
    },
]


@pytest.mark.trio
@pytest.mark.parametrize('test_data', wrong_messages)
async def test_invalid_json_message(test_data):
    test_message = json.dumps(test_data)

    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.send_message(test_message)
        response = await ws.get_message()
        response_message = json.loads(response)
    assert response_message['msgType'] == 'Errors'


@pytest.mark.trio
@pytest.mark.parametrize('test_data', ['hello world!'])
async def test_invalid_message(test_data):
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.send_message(test_data)
        response = await ws.get_message()
        response_message = json.loads(response)

    assert response_message['msgType'] == 'Errors'


@pytest.mark.trio
@pytest.mark.parametrize('test_data', correct_message)
async def test_correct_message(test_data):
    test_message = json.dumps(test_data)
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.send_message(test_message)
        response = await ws.get_message()
        response_message = json.loads(response)
    assert response_message['msgType'] == 'Buses'
