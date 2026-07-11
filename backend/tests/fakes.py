class FakeStorage:
    """In-memory stand-in matching app.storage.Storage's interface."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def ensure_bucket(self):
        pass

    def put_bytes(self, key, data, content_type=None):
        self.objects[key] = bytes(data)

    def get_bytes(self, key):
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]

    def head(self, key):
        if key not in self.objects:
            raise KeyError(key)
        return len(self.objects[key])

    def stream(self, key, start=None, end=None, chunk_size=1024 * 1024):
        data = self.get_bytes(key)
        if start is not None:
            data = data[start : (end + 1) if end is not None else None]
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def delete_prefix(self, prefix):
        for key in [k for k in self.objects if k.startswith(prefix)]:
            del self.objects[key]
