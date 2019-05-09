from threading import Lock


class Channel(object):
    PENDING = "pending"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    def __init__(self,
                 name,
                 client,
                 on_subscribe,
                 on_unsubscribe):
        self._state = Channel.PENDING
        self._name = name
        self._client = client
        self._on_subscribe = on_subscribe
        self._on_unsubscribe = on_unsubscribe

        self._subscriptions = set()
        self._subscription_lock = Lock()

        self._client.on("#publish", self._publish_callback)

    @property
    def state(self):
        return self._state

    @property
    def name(self):
        return self._name

    def _subscribe_callback(self, name, error, data):
        if error:
            self._state = Channel.UNSUBSCRIBED
        else:
            self._state = Channel.SUBSCRIBED
            self._on_subscribe()

    def _publish_callback(self, name, data):
        if name != '#publish':
            return

        if "channel" not in data or data["channel"] != self._name:
            return

        for subscription in self._subscriptions:
            channel_data = data["data"] if "data" in data else None
            subscription(self._name, channel_data)

    def subscribe(self, callback):
        with self._subscription_lock:
            self._subscriptions.add(callback)

            if len(self._subscriptions) > 1:
                return

        self._state = Channel.PENDING
        self._client.emit("#subscribe", {"channel": self._name}, self._subscribe_callback)

    def unsubscribe(self, callback):
        with self._subscription_lock:
            self._subscriptions.remove(callback)

            if len(self._subscriptions) > 0:
                return

        self._client.emit("#unsubscribe", {"channel": self._name})
        self._state = Channel.UNSUBSCRIBED
        self._on_unsubscribe()
