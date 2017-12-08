import logging
from subprocess import PIPE, Popen

from lxml import etree

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.mediaconch')


def run_mediaconch(filename, policy=None):
    cmd = 'mediaconch -fx -p {policy} {filename}'.format(policy=policy, filename=filename)
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
    def validate(self, filepath):
        policy = self.context
        out, _, _ = run_mediaconch(filepath, policy)

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(out, parser=parser)

        passed = get_outcome(root)
        message = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

        if not passed:
            raise ValidationError(message)

        return message
