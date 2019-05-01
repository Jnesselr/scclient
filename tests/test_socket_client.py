import json
from threading import Event, Thread
from unittest import mock
from unittest.mock import Mock, MagicMock, call

import pytest
from websocket import WebSocketApp

from scclient import SocketClient
from scclient.channel import Channel


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
    def test_connect_does_not_create_new_thread_if_existing_one_is_alive(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws_thread = Mock(Thread)
        ws_thread.is_alive.return_value = True
        client._ws_thread = ws_thread

        client.connect()

        assert client._ws_thread is ws_thread
        client._ws_thread.start.assert_not_called()

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_connect_does_create_new_thread_if_existing_one_is_dead(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws_thread = Mock(Thread)
        ws_thread.is_alive.return_value = False
        client._ws_thread = ws_thread

        client.connect()

        assert client._ws_thread is not ws_thread
        ws.run_forever.assert_called_once_with()

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_open_sends_handshake(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        client._internal_on_open()

        expected_handshake = {
            "event": "#handshake",
            "data": {
                "authToken": None,
            },
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(expected_handshake, sort_keys=True))

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_open_resets_cid_each_time(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        client._internal_on_open()
        client._internal_on_open()

        expected_handshake = {
            "event": "#handshake",
            "data": {
                "authToken": None,
            },
            "cid": 1,
        }

        json_expected_handshake = json.dumps(expected_handshake, sort_keys=True)

        ws.send.assert_has_calls([
            call(json_expected_handshake),
            call(json_expected_handshake),
        ])

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
    def test_handshake_response_and_close_manages_connected_and_id_property(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        assert client.id is None
        assert not client.connected

        client._internal_on_open()

        assert client.id is None
        assert not client.connected

        handshake_response = {
            "id": "some_id",
            "isAuthenticated": False,
            "pingTimeout": 10000,
        }

        client._internal_handshake_response("#handshake", None, handshake_response)

        assert client.id == "some_id"
        assert client.connected

        client._internal_on_close()

        assert client.id is None
        assert not client.connected

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_open_registers_handshake_response_callback(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        assert client.id is None

        message = {
            "rid": 1,
            "data": {
                "id": "some_id",
                "isAuthenticated": False,
                "pingTimeout": 10000,
            }
        }

        client._internal_on_open()
        client._internal_on_message(json.dumps(message))

        assert client.id == "some_id"

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_connect_calls_on_connect_when_handshake_response_occurs(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_connect_callback = MagicMock()
        client.on_connect(on_connect_callback)

        message = {
            "rid": 1,
            "data": {
                "id": "some_id",
                "isAuthenticated": False,
                "pingTimeout": 10000,
            }
        }

        # This connect call doesn't do much, as the thread it starts exits immediately.
        # We only call it to verify that the on connect callback isn't called yet.
        client.connect()
        client._internal_on_open()

        on_connect_callback.assert_not_called()

        client._internal_on_message(json.dumps(message))

        on_connect_callback.assert_called_once_with(client)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_disconnect_calls_on_disconnect(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_disconnect_callback = MagicMock()
        client.on_disconnect(on_disconnect_callback)

        client.disconnect()

        on_disconnect_callback.assert_not_called()

        client._internal_on_close()

        on_disconnect_callback.assert_called_once_with(client)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_on_message_responds_to_ping_with_pong(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        client._internal_on_message("#1")

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
            "error": error_text,
            "data": data_text,
        }

        client._internal_on_message(json.dumps(response_payload))

        callback.assert_called_once_with(my_event_name, error_text, data_text)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_emitting_event_without_callback_does_not_fail_or_call_different_callback(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        callback = MagicMock()
        my_event_name = "my_event"
        my_event_data = {}

        client.emit(my_event_name, my_event_data, callback)

        error_text = "This is an error"
        data_text = "This is some data"
        response_payload = {
            "rid": 9001,  # No callback should be assigned to this number
            "error": error_text,
            "data": data_text,
        }

        client._internal_on_message(json.dumps(response_payload))

        callback.assert_not_called()

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_emit_calls_on_handler(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_event_name = "some_random_event"
        client.on(my_event_name, callback)

        callback.assert_not_called()

        my_event_data = {
            "key": "value",
        }
        payload = {
            "event": my_event_name,
            "data": my_event_data,
            "cid": 1,
        }

        client._internal_on_message(json.dumps(payload, sort_keys=True))

        callback.assert_called_once_with(my_event_name, my_event_data)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_emit_increments_cid(self, socket_app):
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

        expected_payload_1 = {
            "event": my_event_name,
            "data": my_event_data,
            "cid": 1,
        }

        expected_payload_2 = expected_payload_1.copy()
        expected_payload_2["cid"] = 2
        client.emit(my_event_name, my_event_data, callback)

        ws.send.assert_has_calls([
            call(json.dumps(expected_payload_1, sort_keys=True)),
            call(json.dumps(expected_payload_2, sort_keys=True)),
        ])

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_reconnect_defaults(self, socket_app):
        client = SocketClient("test_url")

        assert not client.reconnect_enabled
        assert client.reconnect_delay == 2

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_reconnect_kwargs(self, socket_app):
        client = SocketClient("test_url",
                              reconnect_enabled=True,
                              reconnect_delay=5)

        assert client.reconnect_enabled
        assert client.reconnect_delay == 5

    @mock.patch('scclient.socket_client.WebSocketApp')
    @mock.patch('scclient.socket_client.time')
    def test_reconnect_is_called_until_it_is_disabled(self, time_patch, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url",
                              reconnect_enabled=True,
                              reconnect_delay=0.001)

        count = 0
        reconnect_disabled_event = Event()

        def run_forever_side_effect():
            nonlocal client
            nonlocal count
            nonlocal reconnect_disabled_event
            count = count + 1
            if count == 5:
                client.reconnect_enabled = False
                reconnect_disabled_event.set()
            if count >= 6:
                pytest.fail("This function should not have been called this many times! Is reconnect_enabled being "
                            "checked?")

        ws.run_forever.side_effect = run_forever_side_effect

        client.connect()

        reconnect_disabled_event.wait(0.5)
        assert reconnect_disabled_event.is_set()

        assert not client.reconnect_enabled
        time_patch.sleep.assert_has_calls([call(client.reconnect_delay)] * 4)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_disconnecting_manually_disables_reconnects(self, socket_app):
        client = SocketClient("test_url",
                              reconnect_enabled=True)

        assert client.reconnect_enabled

        client.disconnect()

        assert not client.reconnect_enabled

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_publish_sends_payload_to_ws(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        my_channel = "test-channel"
        my_data = {
            "key": "value",
        }

        client.publish(my_channel, my_data)

        payload = {
            "event": "#publish",
            "data": {
                "channel": my_channel,
                "data": my_data,
            },
            "cid": 1
        }

        ws.send.assert_called_once_with(json.dumps(payload, sort_keys=True))

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_publish_sends_payload_to_ws_with_callback(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        my_channel = "test-channel"
        my_data = {
            "key": "value",
        }
        callback = MagicMock()

        client.publish(my_channel, my_data, callback)

        payload = {
            "event": "#publish",
            "data": {
                "channel": my_channel,
                "data": my_data,
            },
            "cid": 1
        }

        ws.send.assert_called_once_with(json.dumps(payload, sort_keys=True))

        callback.assert_not_called()

        error_text = "This is an error"
        data_text = "This is some data"
        response_payload = {
            "rid": 1,
            "error": error_text,
            "data": data_text,
        }

        client._internal_on_message(json.dumps(response_payload))

        callback.assert_called_once_with(my_channel, error_text, data_text)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_publish_increments_cid(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        ws.send.assert_not_called()

        my_channel = "test-channel"
        my_data = {
            "key": "value",
        }
        callback = MagicMock()

        client.publish(my_channel, my_data, callback)

        expected_payload_1 = {
            "event": "#publish",
            "data": {
                "channel": my_channel,
                "data": my_data,
            },
            "cid": 1,
        }
        expected_payload_2 = expected_payload_1.copy()
        expected_payload_2["cid"] = 2
        client.publish(my_channel, my_data, callback)

        ws.send.assert_has_calls([
            call(json.dumps(expected_payload_1, sort_keys=True)),
            call(json.dumps(expected_payload_2, sort_keys=True)),
        ])

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_subscribing_to_a_channel_sends_subscribe_payload(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_channel_name = "test-channel"
        channel = client.subscribe(my_channel_name, callback)

        assert channel is client.channels[my_channel_name]

        expected_payload = {
            "event": "#subscribe",
            "data": {
                "channel": my_channel_name,
            },
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(expected_payload, sort_keys=True))
        callback.assert_not_called()

        assert channel.status == Channel.PENDING

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_subscribing_to_a_channel_twice_sends_subscribe_payload_once(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback_1 = MagicMock()
        callback_2 = MagicMock()

        my_channel_name = "test-channel"
        channel_1 = client.subscribe(my_channel_name, callback_1)
        channel_2 = client.subscribe(my_channel_name, callback_2)

        assert channel_1 is channel_2

        expected_payload = {
            "event": "#subscribe",
            "data": {
                "channel": my_channel_name,
            },
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(expected_payload, sort_keys=True))
        callback_1.assert_not_called()

        assert channel_1.status == Channel.PENDING

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_subscribing_to_a_channel_calls_the_callback_on_publish(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_channel_name = "test-channel"
        client.subscribe(my_channel_name, callback)

        callback.assert_not_called()

        my_data = {
            "key": "value",
        }
        incoming_message = {
            "event": "#publish",
            "data": {
                "channel": my_channel_name,
                "data": my_data,
            }
        }

        client._internal_on_message(json.dumps(incoming_message, sort_keys=True))

        callback.assert_called_once_with(my_channel_name, my_data)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_from_a_channel_sends_unsubscribe_payload(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_channel_name = "test-channel"
        channel = client.subscribe(my_channel_name, callback)

        assert my_channel_name in client.channels
        assert channel.status == Channel.PENDING

        client.unsubscribe(my_channel_name, callback)

        assert my_channel_name in client.channels
        assert channel.status == Channel.UNSUBSCRIBED

        subscribe_payload = {
            "event": "#subscribe",
            "data": {
                "channel": my_channel_name,
            },
            "cid": 1,
        }

        unsubscribe_payload = {
            "event": "#unsubscribe",
            "data": {
                "channel": my_channel_name,
            },
        }

        ws.send.assert_has_calls([
            call(json.dumps(subscribe_payload, sort_keys=True)),
            call(json.dumps(unsubscribe_payload, sort_keys=True)),
        ])

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_from_a_channel_sends_unsubscribe_payload_after_all_unsubscribes(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback_1 = MagicMock()
        callback_2 = MagicMock()

        my_channel_name = "test-channel"
        channel = client.subscribe(my_channel_name, callback_1)
        client.subscribe(my_channel_name, callback_2)

        assert channel.status == Channel.PENDING

        subscribe_payload = {
            "event": "#subscribe",
            "data": {
                "channel": my_channel_name,
            },
            "cid": 1,
        }

        ws.send.assert_called_once_with(json.dumps(subscribe_payload, sort_keys=True))

        client.unsubscribe(my_channel_name, callback_1)

        assert channel.status == Channel.PENDING

        # Still just the one call
        ws.send.assert_called_once_with(json.dumps(subscribe_payload, sort_keys=True))

        client.unsubscribe(my_channel_name, callback_2)

        assert channel.status == Channel.UNSUBSCRIBED

        unsubscribe_payload = {
            "event": "#unsubscribe",
            "data": {
                "channel": my_channel_name,
            },
        }

        ws.send.assert_has_calls([
            call(json.dumps(subscribe_payload, sort_keys=True)),
            call(json.dumps(unsubscribe_payload, sort_keys=True)),
        ])

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_from_a_channel_means_callback_will_not_be_called_again(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_channel = "test-channel"
        client.subscribe(my_channel, callback)

        my_data = {
            "key": "value",
        }
        incoming_message = {
            "event": "#publish",
            "data": {
                "channel": my_channel,
                "data": my_data,
            },
        }

        client._internal_on_message(json.dumps(incoming_message, sort_keys=True))
        callback.assert_called_once_with(my_channel, my_data)

        client.unsubscribe(my_channel, callback)

        # The previous call still exists, but no new calls should have been made
        client._internal_on_message(json.dumps(incoming_message, sort_keys=True))
        callback.assert_called_once_with(my_channel, my_data)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_then_resubscribing_to_a_channel_resends_subscription_payload(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")

        callback = MagicMock()

        my_channel_name = "test-channel"
        channel = client.subscribe(my_channel_name, callback)

        assert channel.status == Channel.PENDING

        client.unsubscribe(my_channel_name, callback)

        assert channel.status == Channel.UNSUBSCRIBED

        client.subscribe(my_channel_name, callback)

        assert channel.status == Channel.PENDING

        channel_data = {
            "channel": my_channel_name,
        }
        first_subscribe_payload = {
            "event": "#subscribe",
            "data": channel_data,
            "cid": 1,
        }
        unsubscribe_payload = {
            "event": "#unsubscribe",
            "data": channel_data
        }
        second_subscribe_payload = {
            "event": "#subscribe",
            "data": channel_data,
            "cid": 2,
        }

        ws.send.assert_has_calls([
            call(json.dumps(first_subscribe_payload, sort_keys=True)),
            call(json.dumps(unsubscribe_payload, sort_keys=True)),
            call(json.dumps(second_subscribe_payload, sort_keys=True)),
        ])

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_subscribing_calls_on_subscribe_after_successful_subscription(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_subscribe_callback = MagicMock()
        client.on_subscribe(on_subscribe_callback)

        on_subscribe_callback.assert_not_called()

        channel_name = "test-channel"
        channel = client.subscribe(channel_name, MagicMock())

        on_subscribe_callback.assert_not_called()

        assert channel.status == Channel.PENDING

        successful_subscription_payload = {
            "rid": 1,
        }

        client._internal_on_message(json.dumps(successful_subscription_payload, sort_keys=True))

        assert channel.status == Channel.SUBSCRIBED

        on_subscribe_callback.assert_called_once_with(client, channel_name)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_calls_on_unsubscribe_immediately(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_unsubscribe_callback = MagicMock()
        client.on_unsubscribe(on_unsubscribe_callback)

        on_unsubscribe_callback.assert_not_called()

        channel_name = "test-channel"
        callback = MagicMock()
        client.subscribe(channel_name, callback)
        client.unsubscribe(channel_name, callback)

        on_unsubscribe_callback.assert_called_once_with(client, channel_name)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_subscribing_calls_on_subscribe_only_for_first_event(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_subscribe_callback = MagicMock()
        client.on_subscribe(on_subscribe_callback)

        on_subscribe_callback.assert_not_called()

        channel_name = "test-channel"
        channel = client.subscribe(channel_name, MagicMock())
        client.subscribe(channel_name, MagicMock())

        assert channel.status == Channel.PENDING

        successful_subscription_payload = {
            "rid": 1,
        }

        client._internal_on_message(json.dumps(successful_subscription_payload, sort_keys=True))

        on_subscribe_callback.assert_called_once_with(client, channel_name)

    @mock.patch('scclient.socket_client.WebSocketApp')
    def test_unsubscribing_calls_on_unsubscribe_only_after_last_event(self, socket_app):
        ws = Mock(WebSocketApp)
        socket_app.return_value = ws

        client = SocketClient("test_url")
        on_unsubscribe_callback = MagicMock()
        client.on_unsubscribe(on_unsubscribe_callback)

        on_unsubscribe_callback.assert_not_called()

        channel_name = "test-channel"
        callback_1 = MagicMock()
        callback_2 = MagicMock()

        client.subscribe(channel_name, callback_1)
        client.subscribe(channel_name, callback_2)
        client.unsubscribe(channel_name, callback_1)
        client.unsubscribe(channel_name, callback_2)

        on_unsubscribe_callback.assert_called_once_with(client, channel_name)
