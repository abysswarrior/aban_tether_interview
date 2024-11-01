class MockRedis:
    def __init__(self):
        self.data = {}

    def zadd(self, name, mapping):
        if name not in self.data:
            self.data[name] = {}
        self.data[name].update(mapping)
        return True

    def zrange(self, name, start, end, withscores=False):
        if name not in self.data:
            return []
        return list(self.data[name].keys())

    def delete(self, *names):
        for name in names:
            if name in self.data:
                del self.data[name]
        return True

    def pipeline(self):
        return MockRedisPipeline(self)


class MockRedisPipeline:
    def __init__(self, redis_instance):
        self.redis_instance = redis_instance
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commands = []
        return False

    def multi(self):
        return self

    def zadd(self, name, mapping):
        self.commands.append(('zadd', name, mapping))
        return True

    def delete(self, *names):
        self.commands.append(('delete', names))
        return True

    def execute(self):
        results = []
        for cmd, *args in self.commands:
            if cmd == 'zadd':
                results.append(self.redis_instance.zadd(args[0], args[1]))
            elif cmd == 'delete':
                results.append(self.redis_instance.delete(*args[0]))
        self.commands = []
        return results
