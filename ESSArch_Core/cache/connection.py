from django_redis.pool import ConnectionFactory


class FakeConnectionFactory(ConnectionFactory):
    def get_connection(self, params):
        return self.redis_client_cls(**self.redis_client_cls_kwargs)
