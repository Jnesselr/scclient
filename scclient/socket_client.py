import collections
import json
import time
from threading import Lock, Thread

from websocket import WebSocketApp

from scclient.channel import Channel
from scclient.event_listener import EventListener


class ChannelsRepository(collections.Mapping):
    def __init__(self, new_channel_function):
        self._channels = {}
        self._new_channel_function = new_channel_function
        self._lock = Lock()

    def __getitem__(self, key):
        with self._lock:
            if key not in self._channels:
                self._channels[key] = self._new_channel_function(key)
        return self._channels[key]

    def __contains__(self, key):
        return self._channels.__contains__(key)

    def __len__(self):
        return len(self._channels)

    def __iter__(self):
        return self._channels.__iter__()


class CallbackWrapper(object):
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback

    def __call__(self, message_object):
        error = message_object["error"] if "error" in message_object else None
        data = message_object["data"] if "data" in message_object else None
        self.callback(self.name, error, data)


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

        self._event_based_callbacks = collections.defaultdict(set)

        self._id_based_callbacks = collections.defaultdict(list)
        self._on_connect_event = EventListener()
        self._on_disconnect_event = EventListener()
        self._on_subscribe_event = EventListener()
        self._on_unsubscribe_event = EventListener()

        self._reconnect_enabled = bool(reconnect_enabled)
        self._reconnect_delay = float(reconnect_delay)

        self._repository = ChannelsRepository(self._new_channel)

    def _new_channel(self, name):
        return Channel(name=name,
                       client=self,
                       on_subscribe=lambda: self._on_subscribe_event(self, name),
                       on_unsubscribe=lambda: self._on_unsubscribe_event(self, name))

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
        return self._repository

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

            self._id_based_callbacks[cid].append(CallbackWrapper(event, callback))

        self._ws.send(json.dumps(payload, sort_keys=True))

    def on(self, event, callback):
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
            self._id_based_callbacks[cid].append(CallbackWrapper(channel, callback))

        self._ws.send(json.dumps(payload, sort_keys=True))

    def subscribe(self, channel_name, callback):
        self._repository[channel_name].subscribe(callback)
        return self._repository[channel_name]

    def unsubscribe(self, channel_name, callback):
        self._repository[channel_name].unsubscribe(callback)

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

        callback_wrapper = CallbackWrapper(handshake_event_name, self._internal_handshake_response)
        self._id_based_callbacks[cid].append(callback_wrapper)
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
            for callback_wrapper in self._id_based_callbacks[message_object["rid"]]:
                callback_wrapper(message_object)

        if "event" not in message_object:
            return

        event_name = message_object["event"]
        message_data = message_object["data"] if "data" in message_object else None

        if event_name in self._event_based_callbacks:
            for callback in self._event_based_callbacks[event_name]:
                callback(event_name, message_data)
