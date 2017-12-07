import logging
from subprocess import Popen, PIPE

from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.verapdf')


class VeraPDFValidator(BaseValidator):
    def validate(self, filepath):
        policy = '--policyfile "{policy}"'.format(policy=self.context) if self.context else ''
        cmd = 'verapdf {policy} "{file}"'.format(policy=policy, file=filepath)

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()

        if p.returncode:
            raise ValidationError(err)

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(out, parser=parser)

        xpath = '//*[local-name()="{el}" and @*[local-name()="{attr}"] = "false"][1]'.format(el='validationReport', attr='isCompliant')
        failed_validation = root.xpath(xpath)

        xpath = '//*[local-name()="{el}" and @*[local-name()="{attr}"] > 0][1]'.format(el='policyReport', attr='failedChecks')
        failed_policy = root.xpath(xpath)

        minified = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

        if len(failed_validation) or len(failed_policy):
            raise ValidationError(minified)

        return minified
