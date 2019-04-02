from unittest.mock import MagicMock

from scclient.event_listener import EventListener


class TestEventListener(object):
    def test_emitting_an_event_calls_the_listeners(self):
        callback = MagicMock()

        event_listener = EventListener()
        event_listener.listener.add(callback)

        event_listener.emit("event")

        callback.assert_called_once_with("event")

    def test_adding_a_callback_after_an_event_does_not_receive_the_event(self):
        callback = MagicMock()

        event_listener = EventListener()
        event_listener.emit("event")

        event_listener.listener.add(callback)

        callback.assert_not_called()

    def test_removing_a_callback(self):
        callback = MagicMock()

        event_listener = EventListener()

        event_listener.listener.add(callback)

        event_listener.emit("event")

        event_listener.listener.remove(callback)

        event_listener.emit("event2")

        callback.assert_called_once_with("event")

    def test_call_version_of_adding_callback(self):
        callback = MagicMock()

        event_listener = EventListener()
        event_listener.listener(callback)

        event_listener.emit("event")

        callback.assert_called_once_with("event")

    def test_call_version_of_emitting_event(self):
        callback = MagicMock()

        event_listener = EventListener()
        event_listener.listener.add(callback)

        event_listener("event")

        callback.assert_called_once_with("event")

    def test_emitting_multiple_arguments(self):
        callback = MagicMock()

        event_listener = EventListener()
        event_listener.listener.add(callback)

        event_listener("event", "other stuff")

        callback.assert_called_once_with("event", "other stuff")
