import json
import time
from threading import Lock, Thread

from websocket import WebSocketApp

from scclient.channel import Channel
from scclient.event_listener import EventListener


class ChannelWrapper(object):
    def __init__(self):
        self._status_change = EventListener()
        self._channel = Channel(self._status_change.listener)

    @property
    def channel(self):
        return self._channel

    def set_state(self, state):
        self._status_change.emit(state)


class SocketClient(object):
    def __init__(self, url,
                 reconnect_enabled=False,
                 reconnect_delay=2):
        self._ws = WebSocketApp(url,
                                on_open=self._internal_on_open,
                                on_close=self._internal_on_close,
                                on_message=self._internal_on_message)
        self._ws_thread = None
        self._ws_connected = False

        self._cid = 0
        self._cid_lock = Lock()

        self._id = None
        self._auth_token = None

        self._event_based_callbacks = {}
        self._event_based_callback_lock = Lock()

        self._id_based_callbacks = {}
        self._on_connect_event = EventListener()
        self._on_disconnect_event = EventListener()
        self._on_subscribe_event = EventListener()
        self._on_unsubscribe_event = EventListener()

        self._reconnect_enabled = bool(reconnect_enabled)
        self._reconnect_delay = float(reconnect_delay)

        self._subscriptions = {}
        self._channels = {}
        self._subscription_lock = Lock()

    @property
    def id(self):
        return self._id

    @property
    def connected(self):
        return self._ws_connected

    @property
    def reconnect_enabled(self):
        return self._reconnect_enabled

    @reconnect_enabled.setter
    def reconnect_enabled(self, enabled):
        self._reconnect_enabled = bool(enabled)

    @property
    def reconnect_delay(self):
        return self._reconnect_delay

    @property
    def channels(self):
        return dict(map(lambda key: (key, self._channels[key].channel), self._channels))

    @property
    def on_connect(self):
        return self._on_connect_event.listener

    @property
    def on_disconnect(self):
        return self._on_disconnect_event.listener

    @property
    def on_subscribe(self):
        return self._on_subscribe_event.listener

    @property
    def on_unsubscribe(self):
        return self._on_unsubscribe_event.listener

    def connect(self):
        if self._ws_thread is not None and self._ws_thread.is_alive():
            return

        self._ws_thread = Thread(target=self._ws_thread_run, daemon=True)
        self._ws_thread.start()

    def disconnect(self):
        self.reconnect_enabled = False
        # This causes the _ws_thread to stop on its own
        self._ws.close()

    def emit(self, event, data, callback=None):
        payload = {
            "event": event,
            "data": data,
        }

        if callback is not None:
            cid = self._get_next_cid()
            payload["cid"] = cid

            self._id_based_callbacks[cid] = (event, callback)

        self._ws.send(json.dumps(payload, sort_keys=True))

    def on(self, event, callback):
        with self._event_based_callback_lock:
            if event not in self._event_based_callbacks:
                self._event_based_callbacks[event] = set()

            self._event_based_callbacks[event].add(callback)

    def publish(self, channel, data, callback=None):
        cid = self._get_next_cid()
        payload = {
            "event": "#publish",
            "data": {
                "channel": channel,
                "data": data,
            },
            "cid": cid
        }

        if callback is not None:
            self._id_based_callbacks[cid] = (channel, callback)

        self._ws.send(json.dumps(payload, sort_keys=True))

    def subscribe(self, channel_name, callback):
        send_subscribe_payload = False

        with self._subscription_lock:
            if channel_name not in self._subscriptions:
                self._subscriptions[channel_name] = set()
                send_subscribe_payload = True

            if channel_name not in self._channels:
                self._channels[channel_name] = ChannelWrapper()

            self._subscriptions[channel_name].add(callback)

        if send_subscribe_payload:
            self._channels[channel_name].set_state(Channel.PENDING)

            cid = self._get_next_cid()

            payload = {
                "event": "#subscribe",
                "data": {
                    "channel": channel_name,
                },
                "cid": cid,
            }

            def callback(name, error, data):
                self._channels[name].set_state(Channel.SUBSCRIBED)

                self._on_subscribe_event(self, name)

            self._id_based_callbacks[cid] = (channel_name, callback)

            self._ws.send(json.dumps(payload, sort_keys=True))

        return self._channels[channel_name].channel

    def unsubscribe(self, channel_name, callback):
        send_unsubscribe_payload = False

        with self._subscription_lock:
            self._subscriptions[channel_name].remove(callback)

            if len(self._subscriptions[channel_name]) == 0:
                del self._subscriptions[channel_name]
                send_unsubscribe_payload = True

                channel_wrapper = self._channels[channel_name]
                channel_wrapper.set_state(Channel.UNSUBSCRIBED)

        if send_unsubscribe_payload:
            payload = {
                "event": "#unsubscribe",
                "data": {
                    "channel": channel_name,
                },
            }

            self._ws.send(json.dumps(payload, sort_keys=True))

            self._on_unsubscribe_event(self, channel_name)

    def _get_next_cid(self):
        with self._cid_lock:
            self._cid += 1
            return self._cid

    def _ws_thread_run(self):
        while True:
            self._ws.run_forever()
            if self.reconnect_enabled:
                time.sleep(self.reconnect_delay)
            else:
                break

    def _internal_on_open(self):
        with self._cid_lock:
            self._cid = 0
        cid = self._get_next_cid()

        handshake_event_name = "#handshake"
        handshake_object = {
            "event": handshake_event_name,
            "data": {
                "authToken": self._auth_token,
            },
            "cid": cid,
        }

        self._id_based_callbacks[cid] = (handshake_event_name, self._internal_handshake_response)
        self._ws.send(json.dumps(handshake_object, sort_keys=True))

    def _internal_handshake_response(self, event_name, error, response):
        self._id = response["id"]
        self._ws_connected = True

        self._on_connect_event(self)

    def _internal_on_close(self):
        self._id = None
        self._ws_connected = False

        self._on_disconnect_event(self)

    def _internal_on_message(self, message):
        if message == "#1":  # ping
            self._ws.send("#2")  # pong
            return

        message_object = json.loads(message)
        if "rid" in message_object and message_object["rid"] in self._id_based_callbacks:
            callback_tuple = self._id_based_callbacks[message_object["rid"]]
            name = callback_tuple[0]  # Either the event or channel name
            callback = callback_tuple[1]

            error = message_object["error"] if "error" in message_object else None
            data = message_object["data"] if "data" in message_object else None
            callback(name, error, data)

        if "event" not in message_object:
            return

        event_name = message_object["event"]
        message_data = message_object["data"] if "data" in message_object else None

        if event_name == "#publish":
            channel = message_data["channel"]
            channel_data = message_data["data"]

            subscriptions = self._subscriptions[channel] if channel in self._subscriptions else set()
            for subscription in subscriptions:
                subscription(channel, channel_data)

        if event_name in self._event_based_callbacks:
            for callback in self._event_based_callbacks[event_name]:
                callback(event_name, message_data)
