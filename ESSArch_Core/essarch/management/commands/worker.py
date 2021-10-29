import shlex
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload

LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL', 'FATAL')


class Command(BaseCommand):
    help = 'Celery worker'

    def add_arguments(self, parser):
        parser.add_argument('-P', '--pool', default='prefork',
                            choices=('prefork', 'eventlet', 'gevent', 'threads', 'solo'))
        parser.add_argument('--pidfile', default=None)
        parser.add_argument('-f', '--logfile', default=None)
        parser.add_argument('-l', '--loglevel', default='INFO', choices=LOG_LEVELS)
        parser.add_argument('-n', '--hostname', default=None)
        parser.add_argument('-c', '--concurrency', default=None)
        parser.add_argument('-Q', '--queues', default='celery,file_operation,validation')

    def handle(self, *args, **options):
        self.stdout.write('Starting celery worker with autoreload...')
        autoreload.run_with_reloader(self._restart_celery, **options)

    def _restart_celery(self, queues, concurrency, hostname, loglevel, logfile, pidfile, pool, *args, **kwargs):
        kill_worker_cmd = 'pkill -9 -f "essarch worker"'
        subprocess.call(shlex.split(kill_worker_cmd))
        start_worker_cmd = "essarch worker"
        if queues is not None:
            start_worker_cmd = start_worker_cmd + ' --queues %s' % queues
        if concurrency is not None:
            start_worker_cmd = start_worker_cmd + ' --concurrency %s' % concurrency
        if hostname is not None:
            start_worker_cmd = start_worker_cmd + ' --hostname %s' % hostname
        if loglevel is not None:
            start_worker_cmd = start_worker_cmd + ' --loglevel %s' % loglevel
        if logfile is not None:
            start_worker_cmd = start_worker_cmd + ' --logfile %s' % logfile
        if pidfile is not None:
            start_worker_cmd = start_worker_cmd + ' --pidfile %s' % pidfile
        if pool is not None:
            start_worker_cmd = start_worker_cmd + ' --pool %s' % pool
        self.stdout.write('start_worker_cmd: %s' % start_worker_cmd)
        subprocess.call(shlex.split(start_worker_cmd))
