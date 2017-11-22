from subprocess import Popen, PIPE

from lxml import etree

def validate_file(filename, policy=None):
    cmd = 'mediaconch -fx -p {policy} {filename}'.format(policy=policy, filename=filename)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    root = etree.fromstring(out)
    passed = len(root.xpath('//*[@outcome="fail"][1]')) == 0
    return passed, out
