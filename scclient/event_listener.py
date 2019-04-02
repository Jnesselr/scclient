from typing import Set


class Listener(object):
    def __init__(self, callbacks: Set):
        self._callbacks = callbacks

    def add(self, callback):
        self._callbacks.add(callback)

    def remove(self, callback):
        self._callbacks.remove(callback)

    def __call__(self, callback):
        self.add(callback)


class EventListener(object):
    def __init__(self):
        self._callbacks = set()
        self._listener = Listener(self._callbacks)

    @property
    def listener(self):
        return self._listener

    def emit(self, *args):
        for callback in self._callbacks:
            callback(*args)

    def __call__(self, *args):
        self.emit(*args)
