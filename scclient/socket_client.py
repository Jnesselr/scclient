import json
from threading import Lock, Thread

from websocket import WebSocketApp

from scclient.event_listener import EventListener


class SocketClient(object):
    def __init__(self, url):
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

        self._callbacks = {}
        self._on_connect_event = EventListener()
        self._on_disconnect_event = EventListener()

    @property
    def id(self):
        return self._id

    @property
    def connected(self):
        return self._ws_connected

    @property
    def on_connect(self):
        return self._on_connect_event.listener

    @property
    def on_disconnect(self):
        return self._on_disconnect_event.listener

    def connect(self):
        self._ws_thread = Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

    def disconnect(self):
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

            self._callbacks[cid] = (event, callback)

        self._ws.send(json.dumps(payload, sort_keys=True))

    def _get_next_cid(self):
        with self._cid_lock:
            self._cid += 1
            return self._cid

    def _internal_on_open(self, ws: WebSocketApp):
        cid = self._get_next_cid()

        handshake_event_name = "#handshake"
        handshake_object = {
            "event": handshake_event_name,
            "data": {
                "authToken": self._auth_token,
            },
            "cid": cid,
        }

        self._callbacks[cid] = (handshake_event_name, self._internal_handshake_response)
        ws.send(json.dumps(handshake_object, sort_keys=True))

    def _internal_handshake_response(self, event_name, error, response):
        self._id = response["id"]
        self._ws_connected = True

        self._on_connect_event(self)

    def _internal_on_close(self, ws: WebSocketApp):
        self._id = None
        self._ws_connected = False

        self._on_disconnect_event(self)

    def _internal_on_message(self, ws: WebSocketApp, message):
        if message == "#1":  # ping
            self._ws.send("#2")  # pong
            return

        message_object = json.loads(message)
        if "rid" in message_object:
            callback_tuple = self._callbacks[message_object["rid"]]
            name = callback_tuple[0]  # Either the event or channel name
            callback = callback_tuple[1]

            error = message_object["error"] if "error" in message_object else None
            data = message_object["data"]
            callback(name, error, data)
