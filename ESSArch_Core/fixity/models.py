import os
import shlex
import uuid
from pathlib import PurePath
from subprocess import PIPE, Popen

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from ESSArch_Core.fields import JSONField
from ESSArch_Core.fixity.exceptions import ConversionError

User = get_user_model()


class ExternalTool(models.Model):
    class Type(models.TextChoices):
        APPLICATION = 'APP'
        DOCKER_IMAGE = 'DOCKER_IMG'

    type = models.CharField(_('type'), max_length=20, choices=Type.choices)
    name = models.CharField(_('name'), max_length=255, unique=True)
    path = models.TextField(_('path'))
    cmd = models.TextField(_('command'))
    enabled = models.BooleanField(_('enabled'))
    form = JSONField(_('form'), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ConversionTool(ExternalTool):
    class Meta:
        verbose_name = _('conversion tool')
        verbose_name_plural = _('conversion tools')

    def prepare_cmd(self, filepath, options):
        kwargs = {
            'input': filepath,
            'input_basename': os.path.basename(filepath),
            'input_dir': os.path.dirname(filepath),
            'input_name': PurePath(filepath).stem,
            'input_ext': ''.join(PurePath(filepath).suffixes)[1:],
        }
        kwargs.update(options)
        return self.cmd.format(**kwargs)

    def _run_application(self, filepath, rootdir, options):
        from ESSArch_Core.util import normalize_path

        old_cwd = os.getcwd()

        try:
            os.chdir(rootdir)
            filepath = normalize_path(filepath)
            cmd = self.path + " " + self.prepare_cmd(filepath, options)
            p = Popen(shlex.split(cmd), shell=True, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                raise ConversionError(err)
        finally:
            os.chdir(old_cwd)

    def _run_docker(self, filepath, rootdir, options):
        import docker
        client = docker.from_env()
        workdir = '/mnt/vol1'

        cmd = self.prepare_cmd(PurePath(filepath).relative_to(rootdir).as_posix(), options)
        client.containers.run(
            self.path,
            cmd,
            volumes={os.path.abspath(rootdir): {'bind': workdir}},
            working_dir=workdir,
            remove=True,
        )

    def run(self, filepath, rootdir, options):
        if self.type == ExternalTool.Type.APPLICATION:
            return self._run_application(filepath, rootdir, options)
        elif self.type == ExternalTool.Type.DOCKER_IMAGE:
            return self._run_docker(filepath, rootdir, options)

        raise ValueError('Unknown tool type')


class Validation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    validator = models.CharField(max_length=255)
    specification = JSONField(null=True)
    time_started = models.DateTimeField(null=True)
    time_done = models.DateTimeField(null=True)
    passed = models.NullBooleanField(null=True)
    required = models.BooleanField(default=True)
    message = models.TextField(max_length=255, blank=True)
    information_package = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.CASCADE,
        null=True,
        related_name='validations',
    )
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
