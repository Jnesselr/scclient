from scclient.event_listener import Listener

class Channel(object):
    PENDING = "pending"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    def __init__(self,
                 status_change_listener):
        """

        :type status_change_listener: Listener
        """
        self._status = Channel.PENDING
        status_change_listener.add(self._on_status_change)

    @property
    def status(self):
        return self._status

    def _on_status_change(self, state):
        self._status = state
