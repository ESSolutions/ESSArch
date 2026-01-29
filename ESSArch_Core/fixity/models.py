import importlib
import os
import shlex
import uuid
from pathlib import PurePath
from subprocess import PIPE, Popen

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from picklefield.fields import PickledObjectField

from ESSArch_Core.fixity.exceptions import (
    CollectionError,
    ConversionError,
    TransformationError,
    ValidationError,
)

User = get_user_model()


class ExternalTool(models.Model):
    class Type(models.TextChoices):
        CONVERSION_TOOL = 'conversion'
        COLLECTION_TOOL = 'collection'
        TRANSFORMATION_TOOL = 'transformation'
        VALIDATION_TOOL = 'validation'

    class EnvironmentType(models.TextChoices):
        CLI_ENV = 'cli'
        PYTHON_ENV = 'python'
        DOCKER_ENV = 'docker'
        TASK_ENV = 'task'

    type = models.CharField(_('type'), max_length=20, choices=Type.choices)
    name = models.CharField(_('name'), max_length=255, unique=True)
    description = models.TextField(_('description'), blank=True)
    path = models.TextField(_('path'))
    cmd = models.TextField(_('options, or command'))
    enabled = models.BooleanField(_('enabled'), default=True)
    environment = models.CharField(_('environment'), max_length=20,
                                   default=EnvironmentType.CLI_ENV, choices=EnvironmentType.choices)
    file_processing = models.BooleanField(_('file processing (pattern)'), default=False)
    delete_original = models.BooleanField(_('remove orginal file after processing'), default=False)
    form = models.JSONField(_('form'), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


def ActionTool_form_default():
    return [
        dict({
            "key": "path",
            "type": "input",
            "templateOptions": dict({
                "label": "PATH_i18n",
                "required": "true"
            }),
            "expressionProperties": dict({
                "templateOptions.label": "\"PATH\" | translate"
            })
        })
    ]


class ActionTool(ExternalTool):
    form = models.JSONField(_('form'), null=True, blank=True, default=ActionTool_form_default)

    class Meta:
        verbose_name = _('action tool')
        verbose_name_plural = _('action tools')

    def prepare_cmd(self, filepath, options):
        kwargs = {
            'input': filepath,  # 'test1/test2/kanin.jpg'
            'input_basename': os.path.basename(filepath),   # 'kanin.jpg'
            'input_dir': os.path.dirname(filepath),     # 'test1/test2'
            'input_name': PurePath(filepath).stem,      # 'kanin'
            'input_ext': ''.join(PurePath(filepath).suffixes)[1:],  # 'jpg'
        }
        kwargs.update(options)
        if isinstance(self.cmd, str):
            return self.cmd.format(**kwargs)
        elif isinstance(self.cmd, dict):
            return {k: v.format(**kwargs) for k, v in self.cmd.items()}
        else:
            raise TypeError(f"Invalid self.cmd type: {type(self.cmd)}")

    def _run_application(self, filepath, rootdir, options, t=None, ip=None):
        from ESSArch_Core.util import normalize_path

        old_cwd = os.getcwd()
        try:
            os.chdir(rootdir)
            filepath = normalize_path(filepath)
            cmd = self.path + " " + self.prepare_cmd(filepath, options)
            p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                message = 'Command "{cmd}" exited with returncode "{returncode}" and error message "{err}"'.format(
                    cmd=cmd,
                    returncode=p.returncode,
                    err=err
                )
                if self.type == ExternalTool.Type.CONVERSION_TOOL:
                    raise ConversionError(message)
                elif self.type == ExternalTool.Type.COLLECTION_TOOL:
                    raise CollectionError(message)
                elif self.type == ExternalTool.Type.TRANSFORMATION_TOOL:
                    raise TransformationError(message)
                elif self.type == ExternalTool.Type.VALIDATION_TOOL:
                    raise ValidationError(message)
        finally:
            os.chdir(old_cwd)

    def _run_python(self, filepath, rootdir, options, t=None, ip=None, context=None):
        from ESSArch_Core.util import normalize_path

        old_cwd = os.getcwd()
        try:
            os.chdir(rootdir)
            filepath = normalize_path(filepath)
            if not context and '_context' in options.keys():
                context = options.pop('_context')
            cmd = self.prepare_cmd(filepath, options)
            if isinstance(cmd, str):
                cmd = shlex.split(cmd)

            try:
                [module, task] = self.path.rsplit('.', 1)
                p = getattr(importlib.import_module(module), task)(task=t, ip=ip, context=context)
                if self.type == ExternalTool.Type.CONVERSION_TOOL and isinstance(cmd, dict):
                    p.convert(**cmd)
                elif self.type == ExternalTool.Type.CONVERSION_TOOL and isinstance(cmd, list):
                    p.convert(*cmd)
                elif self.type == ExternalTool.Type.COLLECTION_TOOL and isinstance(cmd, dict):
                    p.collect(**cmd)
                elif self.type == ExternalTool.Type.COLLECTION_TOOL and isinstance(cmd, list):
                    p.collect(*cmd)
                elif self.type == ExternalTool.Type.TRANSFORMATION_TOOL and isinstance(cmd, dict):
                    p.transform(**cmd)
                elif self.type == ExternalTool.Type.TRANSFORMATION_TOOL and isinstance(cmd, list):
                    p.transform(*cmd)
                elif self.type == ExternalTool.Type.VALIDATION_TOOL and isinstance(cmd, dict):
                    p.validate(**cmd)
                elif self.type == ExternalTool.Type.VALIDATION_TOOL and isinstance(cmd, list):
                    p.validate(*cmd)
                else:
                    raise ValueError(cmd)
            except Exception as err:
                message = 'Module "{module}" command "{cmd}" exited with error message "{err}"'.format(
                    module=self.path,
                    cmd=cmd,
                    err=err
                )
                if self.type == ExternalTool.Type.CONVERSION_TOOL:
                    raise ConversionError(message)
                elif self.type == ExternalTool.Type.COLLECTION_TOOL:
                    raise CollectionError(message)
                elif self.type == ExternalTool.Type.TRANSFORMATION_TOOL:
                    raise TransformationError(message)
                elif self.type == ExternalTool.Type.VALIDATION_TOOL:
                    raise ValidationError(message)
        finally:
            os.chdir(old_cwd)

    def _run_docker(self, filepath, rootdir, options, t=None, ip=None):
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

    def run(self, filepath, rootdir, options, t=None, ip=None, context=None):
        if self.environment == ActionTool.EnvironmentType.CLI_ENV:
            return self._run_application(filepath, rootdir, options, t, ip)
        elif self.environment == ActionTool.EnvironmentType.DOCKER_ENV:
            return self._run_docker(filepath, rootdir, options, t, ip)
        elif self.environment == ActionTool.EnvironmentType.PYTHON_ENV:
            return self._run_python(filepath, rootdir, options, t, ip, context)

        raise ValueError('Unknown tool type')


class Validation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=1024)
    validator = models.CharField(max_length=255)
    specification = models.JSONField(null=True)
    time_started = models.DateTimeField(null=True)
    time_done = models.DateTimeField(null=True)
    passed = models.BooleanField(null=True)
    required = models.BooleanField(default=True)
    message = PickledObjectField(null=True, default=None, editable=False)
    information_package = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.CASCADE,
        null=True,
        related_name='validations',
    )

    class Meta:
        get_latest_by = ['time_done']

    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
