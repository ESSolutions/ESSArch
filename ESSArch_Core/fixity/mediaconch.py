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
        msg = root.xpath('//*[local-name()="rule"][@outcome="fail"][1]')[0]
        msg = '"%s" failed with an actual value of %s%s"%s"' % (msg.get('name'), msg.get('value'), msg.get('operator'), msg.get('actual'))

    return passed, msg
