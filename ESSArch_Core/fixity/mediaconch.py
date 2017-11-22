from subprocess import Popen, PIPE

from lxml import etree

def validate_file(filename, policy=None):
    cmd = 'mediaconch -fx -p {policy} {filename}'.format(policy=policy, filename=filename)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.XML(out, parser=parser)
    passed = len(root.xpath('//*[@outcome="fail"][1]')) == 0
    return passed, etree.tostring(root)
