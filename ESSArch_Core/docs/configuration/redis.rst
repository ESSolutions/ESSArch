=====
Redis
=====

Set ``REDIS_URL`` in the application configuration file using one of the
following standard `redis-py`_ formats:


.. code-block:: txt

    redis://[:password]@localhost:6379/0
    rediss://[:password]@localhost:6379/0
    unix://[:password]@/path/to/socket.sock?db=0

.. _redis-py: https://pypi.org/project/redis/
