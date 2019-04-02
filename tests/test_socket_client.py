import json
from unittest import mock
from unittest.mock import Mock, MagicMock

from websocket import WebSocketApp

from scclient import SocketClient


class TestSocketClient(object):
    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_socket_is_created_with_correct_parameters(self, socket_app):
        url = "wss://foo.com/socket/"
        client = SocketClient(url)

        assert client is not None
        socket_app.assert_called_once_with(url,
                                           on_open=client._internal_on_open,
                                           on_close=client._internal_on_close,
                                           on_message=client._internal_on_message)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_connect_starts_ws_thread(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.run_forever.assert_not_called()
        ws.send.assert_not_called()

        client.connect()
        client._ws_thread.join(0.001)

        ws.run_forever.assert_called_once_with()

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_open_sends_handshake(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        client._internal_on_open(ws)

        expected_handshake = {
            "event": "#handshake",
            "data": {
                "authToken": None,
            },
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(expected_handshake, sort_keys=True))

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_disconnect_closes_websocket(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        client.connect()

        ws.close.assert_not_called()

        client.disconnect()

        ws.close.assert_called_once_with()

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_open_and_close_manages_connected_property(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        assert not client.connected

        client._internal_on_open(ws)

        assert client.connected

        client._internal_on_close(ws)

        assert not client.connected

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_message_responds_to_ping_with_pong(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        client._internal_on_message(ws, "#1")

        ws.send.assert_called_once_with("#2")

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_emitting_event_without_callback_sends_the_correct_payload(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        my_event_name = "my_event"
        my_event_data = {
            "key": "value",
        }

        client.emit(my_event_name, my_event_data)

        expected_payload = {
            "event": my_event_name,
            "data": my_event_data,
        }

        ws.send.assert_called_once_with(json.dumps(expected_payload, sort_keys=True))

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_emitting_event_with_callback_sends_the_correct_payload_and_calls_callback(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        my_event_name = "my_event"
        my_event_data = {
            "key": "value",
        }

        callback = MagicMock()

        client.emit(my_event_name, my_event_data, callback)

        expected_payload = {
            "event": my_event_name,
            "data": my_event_data,
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(expected_payload, sort_keys=True))
        callback.assert_not_called()

        error_text = "This is an error"
        data_text = "This is some data"
        response_payload = {
            "rid": 1,
            "data": {
                "error": error_text,
                "data": data_text,
            },
        }

        client._internal_on_message(ws, json.dumps(response_payload))

        callback.assert_called_once_with(my_event_name, error_text, data_text)
