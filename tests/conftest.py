from unittest import mock
from unittest.mock import MagicMock

import pytest

from scclient import SocketClient


class SocketWrapper(object):
    def __init__(self):
        self.url = "wss://foo.com/socket/"
        ws_class = mock.patch('scclient.socket_client.WebSocketApp').start()
        self.ws = MagicMock()
        ws_class.side_effect = self._propagate_on_handlers

        self.client = SocketClient(self.url)

    def _propagate_on_handlers(self, url, **kwargs):
        """
        The goal of this function is to propagate the on handlers, so that this class can
        call on them without calling in to the private methods of the client. It also verifies
        we're wiring up our websocket client with the internal WebSocketApp at the minor cost of
        being a bit more reliant on the fact that the WebSocketApp sets all of the on_* handlers
        to be publicly accessible.

        :param url: The url we're testing with, which will be self.url
        :param kwargs: The list of args passed into our ws_class mock
        """
        self.ws.url = url
        for arg, value in kwargs.items():
            if not arg.startswith("on"):
                raise NotImplementedError("This only propagates the 'on' method handlers")

            setattr(self.ws, arg, value)

        return self.ws


wrappers = {}


def _get_wrapper(request):
    name = str(request.node.instance) + "_" + request.node.name
    if name not in wrappers:
        wrappers[name] = SocketWrapper()

    return wrappers[name]


@pytest.fixture
def ws(request):
    return _get_wrapper(request).ws


@pytest.fixture
def client(request):
    return _get_wrapper(request).client
