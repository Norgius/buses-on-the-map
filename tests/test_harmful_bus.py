import json

import pytest
from trio_websocket import open_websocket_url

URL_FOR_BROWSER = 'ws://127.0.0.1:8000'
URL_FOR_BUSES = 'ws://127.0.0.1:8080'

wrong_messages = [
        'hello world!',
        {'some_data': '111newBounds'},
        {"busId": '76e-26', "lat": 39.23623531, "route": '76e'},
        {
            "busId": '76e-26',
            "lat": 111.860268253711,
            "lng": 60,
            "route": '1251a',
        },
]

correct_message = [
    {
        "busId": '76e-26',
        "lat": 55.860268253711,
        "lng": 37.602014843876,
        "route": '1251a',
    },
]


@pytest.mark.trio
@pytest.mark.parametrize('test_data', wrong_messages)
async def test_invalid_json_message(test_data):
    test_message = json.dumps(test_data)

    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
        await ws.send_message(test_message)
        response = await ws.get_message()
        response_message = json.loads(response)

    assert response_message['msgType'] == 'Errors'


@pytest.mark.trio
@pytest.mark.parametrize('test_data', ['hello world!'])
async def test_invalid_message(test_data):
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
        await ws.send_message(test_data)
        response = await ws.get_message()
        response_message = json.loads(response)

    assert response_message['msgType'] == 'Errors'


@pytest.mark.trio
@pytest.mark.parametrize('test_data', correct_message)
async def test_correct_message(test_data):
    test_message = json.dumps(test_data)
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
        await ws.send_message(test_message)
        response = await ws.get_message()
        response_message = json.loads(response)

    assert response_message['msgType'] == 'Success'
