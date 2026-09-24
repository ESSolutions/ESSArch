import logging
import threading

from django.core.cache import cache
from redis.exceptions import LockError, LockNotOwnedError

logger = logging.getLogger('essarch')


class RenewableCacheLock:
    """
    A Redis lock with automatic TTL renewal.

    The lock is acquired with a relatively short timeout and extended
    periodically while the protected code is running.

    The Redis lock uses thread_local=False because the lock is acquired
    in the task thread and renewed from a separate thread.
    """

    def __init__(
        self,
        key,
        timeout=300,
        renew_interval=None,
        logger=None,
    ):
        self.key = key
        self.timeout = timeout

        # Renew well before the TTL expires.
        # Default to one third of the TTL, but never less than 1 second.
        if renew_interval is None:
            renew_interval = max(1, timeout // 3)

        self.renew_interval = renew_interval
        self.logger = logger or logging.getLogger('essarch')

        self.lock = None
        self._stop_event = threading.Event()
        self._renew_thread = None
        self._lost = False

    def acquire(self):
        self.lock = cache.lock(
            self.key,
            timeout=self.timeout,
            thread_local=False,
        )

        acquired = self.lock.acquire()

        if not acquired:
            raise LockError(
                'Could not acquire lock {}'.format(self.key)
            )

        self.logger.debug(
            'Acquired lock %s with TTL %ss, renewing every %ss',
            self.key,
            self.timeout,
            self.renew_interval,
        )

        self._renew_thread = threading.Thread(
            target=self._renew_loop,
            name='essarch-lock-renewer',
            daemon=True,
        )
        self._renew_thread.start()

        return True

    def _renew_loop(self):
        while not self._stop_event.wait(self.renew_interval):
            try:
                self.lock.extend(
                    self.timeout,
                    replace_ttl=True,
                )

                self.logger.debug(
                    'Renewed lock %s for %ss',
                    self.key,
                    self.timeout,
                )

            except LockNotOwnedError:
                self._lost = True

                self.logger.error(
                    'Lost ownership of lock %s while renewing',
                    self.key,
                )
                return

            except Exception:
                self._lost = True

                self.logger.exception(
                    'Unexpected error renewing lock %s',
                    self.key,
                )
                return

    def release(self):
        self._stop_event.set()

        if self._renew_thread is not None:
            self._renew_thread.join(
                timeout=self.renew_interval + 1,
            )

        if self.lock is None:
            return

        try:
            self.lock.release()

            self.logger.debug(
                'Released lock %s',
                self.key,
            )

        except LockNotOwnedError:
            self.logger.warning(
                'Lock %s was no longer owned when releasing',
                self.key,
            )

    def __enter__(self):
        self.acquire()
        return self

    @property
    def lost(self):
        return self._lost

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

        if self._lost and exc_type is None:
            raise LockNotOwnedError(
                'Lock {} was lost while task was running'.format(self.key)
            )

        return False
