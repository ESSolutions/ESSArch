from __future__ import unicode_literals

import errno
import logging
import os
import traceback
from subprocess import PIPE, Popen

from django.utils import timezone
from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.verapdf')


def run_verapdf(filepath, policy=None, validate=True, extract_features=False):
    if not os.path.exists(filepath):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), filepath)

    if policy and not os.path.exists(policy):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), policy)

    policy = '--policyfile "{policy}"'.format(policy=policy) if policy else ''
    extract_features = '-x' if extract_features else ''
    validate = '' if validate else '-o'
    cmd = 'verapdf {validate} {extract_features} {policy} "{file}"'.format(validate=validate, extract_features=extract_features, policy=policy, file=filepath)

    logger.debug(cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


def get_outcome(root):
    xpaths = []

    xpath = '//*[local-name()="batchSummary"]/*[local-name()="{el}" and (@*[local-name()="nonCompliant"] > 0 or @*[local-name()="failedJobs"] > 0)][1]'.format(
        el='validationReports')
    xpaths.append(xpath)

    xpath = '//*[local-name()="batchSummary"]/*[local-name()="{el}" and @*[local-name()="failedJobs"] > 0][1]'.format(el='featureReports')
    xpaths.append(xpath)

    xpath = '//*[local-name()="batchSummary"]/*[local-name()="{el}" and @*[local-name()="failedJobs"] > 0][1]'.format(el='repairReports')
    xpaths.append(xpath)

    xpath = '//*[local-name()="{el}" and @*[local-name()="{attr}"] > 0][1]'.format(el='policyReport', attr='failedChecks')
    xpaths.append(xpath)

    for xpath in xpaths:
        if len(root.xpath(xpath)):
            # atleast one failure, the validation didn't pass
            return False

    return True


class VeraPDFValidator(BaseValidator):
    """
    Runs verapdf on the specified filepath and parses the output to decide
    if it passed or not.

    ``context`` is used to specify the path of a verapdf policy file.
    """

    def validate(self, filepath, expected=None):
        logger.debug("Validating %s with VeraPDF" % filepath)

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
            out, err, returncode = run_verapdf(filepath, self.context)

            if returncode:
                logger.warning("VeraPDF validation of %s failed, %s" % (filepath, err))
                raise ValidationError(err)

            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.XML(out, parser=parser)

            passed = get_outcome(root)
            message = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

            if not passed:
                logger.warning("VeraPDF validation of %s failed, %s" % (filepath, message))
                raise ValidationError(message)
        except Exception:
            val_obj.message = traceback.format_exc()
            raise
        else:
            val_obj.message = message
            logger.info("Successful VeraPDF validation of %s" % filepath)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])

        return message
