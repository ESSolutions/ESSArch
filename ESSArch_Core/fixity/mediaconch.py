from subprocess import Popen, PIPE

from lxml import etree

def validate_file(filename, policy=None):
    cmd = 'mediaconch -fx -p {policy} {filename}'.format(policy=policy, filename=filename)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.XML(out, parser=parser)

    passed = True
    outcome = (root.xpath('//*[@*[local-name() = "outcome"]][1]'))
    if len(outcome):
        passed = outcome[0].attrib['outcome'] == 'pass'

    minified = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    return passed, minified
