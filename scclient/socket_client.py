import json
from threading import Lock, Thread

from websocket import WebSocketApp


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

        self._auth_token = None

    @property
    def connected(self):
        return self._ws_connected

    def connect(self):
        self._ws_thread = Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

    def disconnect(self):
        # This causes the _ws_thread to stop on its own
        self._ws.close()

    def _get_next_cid(self):
        with self._cid_lock:
            self._cid += 1
            return self._cid

    def _internal_on_open(self, ws: WebSocketApp):
        handshake_object = {
            "event": "#handshake",
            "data": {
                "authToken": self._auth_token,
            },
            "cid": self._get_next_cid(),
        }

        ws.send(json.dumps(handshake_object, sort_keys=True))

        self._ws_connected = True

    def _internal_on_close(self, ws: WebSocketApp):
        self._ws_connected = False

    def _internal_on_message(self, ws: WebSocketApp, message):
        if message == "#1":  # ping
            self._ws.send("#2")  # pong
            return
