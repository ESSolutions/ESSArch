import os
from unittest import mock
from unittest.mock import MagicMock

from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.cli.main import (
    beat,
    create_data_directories,
    devserver,
    migrate,
    worker,
)


class CLITest(SimpleTestCase):
    def test_migrate(self):
        runner = CliRunner()

        with mock.patch('ESSArch_Core.cli.main.dj_call_command') as cmd:
            result = runner.invoke(migrate)
            cmd.assert_called_once_with('migrate', interactive=False, verbosity=1)
            self.assertEqual(result.exit_code, 0)

    def test_devserver(self):
        runner = CliRunner()
        addrport = '127.1.2.3:6789'

        with mock.patch('ESSArch_Core.cli.main.dj_call_command') as cmd:
            result = runner.invoke(devserver, [addrport])
            cmd.assert_called_once_with('runserver', addrport=addrport, use_reloader=True)
            self.assertEqual(result.exit_code, 0)

        with mock.patch('ESSArch_Core.cli.main.dj_call_command') as cmd:
            result = runner.invoke(devserver, [addrport, '--noreload'])
            cmd.assert_called_once_with('runserver', addrport=addrport, use_reloader=False)
            self.assertEqual(result.exit_code, 0)

    def test_create_data_directories(self):
        runner = CliRunner()

        with runner.isolated_filesystem() as datadir:
            result = runner.invoke(create_data_directories, ['-p', datadir])
            self.assertEqual(result.exit_code, 0)
            self.assertNotEqual(len(os.listdir(datadir)), 0)

    def test_worker(self):
        runner = CliRunner()

        with mock.patch('celery.app.base.Celery.Worker', return_value=MagicMock(exitcode=0)) as cmd:
            result = runner.invoke(worker)
            cmd.assert_called_once_with(
                logfile=None,
                loglevel='INFO',
                hostname=None,
                concurrency=None,
                queues='celery,file_operation,validation',
                optimization='fair',
                pidfile=None,
                prefetch_multiplier=1,
                pool='prefork',
            )
            self.assertEqual(result.exit_code, 0)

        with mock.patch('celery.app.base.Celery.Worker', return_value=MagicMock(exitcode=0)) as cmd:
            result = runner.invoke(
                worker,
                [
                    '-Q', 'validation',
                    '-c', '5',
                    '-l', 'DEBUG',
                    '-n', 'testhost',
                    '-P', 'gevent',
                    '-f', 'worker.log',
                    '--pidfile', 'worker.pid'
                ],
            )
            cmd.assert_called_once_with(
                logfile='worker.log',
                loglevel='DEBUG',
                hostname='testhost',
                concurrency=5,
                queues='validation',
                optimization='fair',
                pidfile='worker.pid',
                prefetch_multiplier=1,
                pool='gevent',
            )
            self.assertEqual(result.exit_code, 0)

    def test_beat(self):
        runner = CliRunner()

        with mock.patch('celery.app.base.Celery.Beat', return_value=MagicMock(exitcode=0)) as cmd:
            result = runner.invoke(beat)
            cmd.assert_called_once_with(logfile=None, loglevel='INFO', pidfile=None)
            self.assertEqual(result.exit_code, 0)

        with mock.patch('celery.app.base.Celery.Beat', return_value=MagicMock(exitcode=0)) as cmd:
            result = runner.invoke(beat, ['-f', 'beat.log', '-l', 'DEBUG', '--pidfile', 'beat.pid'])
            cmd.assert_called_once_with(logfile='beat.log', loglevel='DEBUG', pidfile='beat.pid')
            self.assertEqual(result.exit_code, 0)
