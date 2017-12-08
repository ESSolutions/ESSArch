import logging
from subprocess import PIPE, Popen

from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.verapdf')


def run_verapdf(filepath, policy=None):
    policy = '--policyfile "{policy}"'.format(policy=policy) if policy else ''
    cmd = 'verapdf {policy} "{file}"'.format(policy=policy, file=filepath)

    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


def get_outcome(root):
    xpath = '//*[local-name()="{el}" and @*[local-name()="{attr}"] = "false"][1]'.format(el='validationReport', attr='isCompliant')
    failed_validation = root.xpath(xpath)

    xpath = '//*[local-name()="{el}" and @*[local-name()="{attr}"] > 0][1]'.format(el='policyReport', attr='failedChecks')
    failed_policy = root.xpath(xpath)

    if len(failed_validation) or len(failed_policy):
        return False

    return True


class VeraPDFValidator(BaseValidator):
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
