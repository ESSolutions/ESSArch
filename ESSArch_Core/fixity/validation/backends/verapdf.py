import errno
import logging
import os
from subprocess import PIPE, Popen

from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.verapdf')


def run_verapdf(filepath, policy=None):
    if not os.path.exists(filename):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), filename)

    if policy and not os.path.exists(policy):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), policy)

    policy = '--policyfile "{policy}"'.format(policy=policy) if policy else ''
    cmd = 'verapdf {policy} "{file}"'.format(policy=policy, file=filepath)

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

    def validate(self, filepath):
        out, err, returncode = run_verapdf(filepath, self.context)

        if returncode:
            raise ValidationError(err)

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(out, parser=parser)

        passed = get_outcome(root)
        message = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

        if not passed:
            raise ValidationError(message)

        return message
