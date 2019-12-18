import errno
import logging
import os
import traceback
from subprocess import PIPE, Popen

import click
from django.utils import timezone
from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.mediaconch')


def run_mediaconch(filename, reporting_element='Mediaconch', output_format='xml', policy=None):
    if not os.path.exists(filename):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), filename)

    if policy and not os.path.exists(policy):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), policy)

    cmd = 'mediaconch --{reporter} --Format={format} -p "{policy}" "{filename}"'.format(
        reporter=reporting_element, format=output_format, policy=policy, filename=filename
    )
    logger.debug(cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


def get_outcome(root):
    passed = True
    outcome = root.xpath('//*[@*[local-name() = "outcome"]][1]')
    if len(outcome):
        passed = outcome[0].attrib['outcome'] == 'pass'

    return passed


class MediaconchValidator(BaseValidator):
    """
    Runs mediaconch on the specified filepath and parses the output to decide
    if it passed or not.

    ``context`` is used to specify the path of a mediaconch policy file.
    """

    def validate(self, filepath, expected=None):
        logger.debug("Validating %s with Mediaconch" % filepath)

        val_obj = Validation.objects.create(
            filename=filepath,
            time_started=timezone.now(),
            validator=self.__class__.__name__,
            required=self.required,
            task=self.task,
            information_package=self.ip,
            responsible=self.responsible,
            specification={
                'context': self.context,
                'options': self.options,
            }
        )

        passed = False
        try:
            out, err, returncode = run_mediaconch(filepath, policy=self.context)

            if returncode:
                logger.warning("Mediaconch validation of %s failed, %s" % (filepath, err))
                raise ValidationError(err)

            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.XML(out, parser=parser)

            passed = get_outcome(root)
            message = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

            if not passed:
                logger.warning("Mediaconch validation of %s failed, %s" % (filepath, message))
                raise ValidationError(message)
        except Exception:
            val_obj.message = traceback.format_exc()
            raise
        else:
            val_obj.message = message
            logger.info("Successful Mediaconch validation of %s" % filepath)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])

        return message

    @staticmethod
    @click.command()
    @click.option('--policy', metavar='INPUT', type=click.Path(exists=True), default=None)
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    def cli(path, policy):
        validator = MediaconchValidator(context=policy)
        try:
            validator.validate(path)
            click.echo('success!')
        except ValidationError as e:
            click.echo(e, err=True)
            for error in e.errors:
                click.echo(error, err=True)
