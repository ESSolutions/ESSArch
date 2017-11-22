from subprocess import Popen, PIPE

from lxml import etree

def validate_file(filename, policy=None):
    cmd = 'mediaconch -fx -p {policy} {filename}'.format(policy=policy, filename=filename)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    root = etree.fromstring(out)
    passed = len(root.xpath('//*[@outcome="fail"][1]')) == 0
    msg = ''

    if not passed:
        failed_rule = root.xpath('//*[local-name()="rule"][@outcome="fail"][1]')
        failed_test = root.xpath('//*[local-name()="test"][@outcome="fail"][1]')
        if len(failed_rule):
            msg = failed_rule[0]
            msg = '"%s" failed with an actual value of %s%s"%s"' % (msg.get('name'), msg.get('value'), msg.get('operator'), msg.get('actual'))
        elif len(failed_test):
            msg = failed_test[0].xpath('//*[local-name()="value"][1]')[0]
            msg = '"%s" failed with offset "%s" and value "%s"' % (msg.get('name'), msg.get('offset'), msg.text)
        else:
            msg = 'Unknown error'


    return passed, msg
