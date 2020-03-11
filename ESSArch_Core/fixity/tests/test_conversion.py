import os
import shutil
import tempfile
from subprocess import PIPE
from unittest import mock

from django.test import TestCase

from ESSArch_Core.fixity.models import ConversionTool
from ESSArch_Core.util import normalize_path


class ConversionJobViewSetRunTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    @mock.patch('ESSArch_Core.fixity.models.Popen')
    def test_application(self, mock_popen):
        popen_obj = mock.MagicMock()
        popen_obj.returncode = 0
        popen_obj.communicate.return_value = ('output', 'error')
        mock_popen.return_value = popen_obj

        t = ConversionTool.objects.create(
            name='ffmpeg', enabled=True, type=ConversionTool.Type.APPLICATION,
            path='ffmpeg', cmd='-i {input} {input_dir}/{input_name}.{output}',
        )
        f = os.path.join(self.datadir, 'foo.mkv')
        t.run(f, self.datadir, {'output': 'mp4'})

        mock_popen.assert_called_once_with(
            ['ffmpeg', f'-i {normalize_path(f)} {normalize_path(os.path.join(os.path.dirname(f), "foo.mp4"))}'],
            shell=True, stdout=PIPE, stderr=PIPE,
        )
