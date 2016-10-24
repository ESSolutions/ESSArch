import os, shutil

from django.test import TestCase

from lxml import etree

from demo import xmlGenerator

from configuration.models import (
    Path,
)

class test_generateXML(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bd = os.path.dirname(os.path.realpath(__file__))
        cls.xmldir = os.path.join(cls.bd,"xmlfiles")
        cls.datadir = os.path.join(cls.bd,"datafiles")
        cls.fname = os.path.join(cls.xmldir, "test.xml")

        shutil.rmtree(cls.xmldir)
        os.mkdir(cls.xmldir)

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(cls.bd, "mime.types")
        )

    def tearDown(self):
        try:
            os.remove(self.fname)
        except:
            pass

    def test_generate_namespaces(self):
        specification = {
            "-name": "foo",
            "-attr": [
                {
                    "-name": "xmlns:xsi",
                    "-req": 1,
                    "#content": [{"var":"xmlns:xsi"}]
                },{
                    "-name": "xsi:schemaLocation",
                    "-req": 1,
                    "#content": [{"var":"xsi:schemaLocation"}]
                },
            ]
        }

        specification_data = {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.w3.org/1999/xlink schemas/xlink.xsd",
        }

        xmlGenerator.createXML(
            specification_data,
            {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()

        xsi_ns = root.nsmap.get("xsi")

        self.assertEqual(xsi_ns, specification_data["xmlns:xsi"])
        self.assertEqual(
            root.attrib.get("{%s}schemaLocation" % xsi_ns),
            specification_data["xsi:schemaLocation"]
        )

    def test_generate_empty_element(self):
        specification = {'-name': "foo"}

        with self.assertRaises(ValueError):
            xmlGenerator.createXML(
                {}, {self.fname: specification}
            )

        self.assertTrue(os.path.exists(self.fname))

    def test_generate_multiple_element_same_name_same_level(self):
        specification = {
            '-name': "foo",
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': 'bar',
                    '-allowEmpty': True,
                },
                {
                    '-name': 'bar#1',
                    '-allowEmpty': True,
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual(len(tree.findall('.//bar')), 2)

    def test_generate_empty_element_with_allowEmpty(self):
        specification = {'-name': "foo", "-allowEmpty": 1}
        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), "<foo/>")

    def test_generate_element_with_content(self):
        specification = {
            '-name': "foo",
            "#content": [
                {"text": "bar"}
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual("<foo>bar</foo>", etree.tostring(tree.getroot()))

    def test_generate_empty_element_with_single_attribute(self):
        specification = {
            '-name': "foo",
            "-attr": [
                {
                    "-name": "bar",
                    "#content": [
                        {
                            "text": "baz"
                        }
                    ]
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual('<foo bar="baz"/>', etree.tostring(tree.getroot()))

    def test_generate_empty_element_with_multiple_attribute(self):
        specification = {
            '-name': "foo",
            "-attr": [
                {
                    "-name": "attr1",
                    "#content": [
                        {
                            "text": "bar"
                        }
                    ]
                },
                {
                    "-name": "attr2",
                    "#content": [
                        {
                            "text": "baz"
                        }
                    ]
                },
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo attr1="bar" attr2="baz"/>',
            etree.tostring(tree.getroot())
        )

    def test_generate_element_with_content_and_attribute(self):
        specification = {
            '-name': "foo",
            '#content': [{'text': 'bar'}],
            '-attr': [
                {
                    "-name": "attr1",
                    "#content": [
                        {
                            "text": "baz"
                        }
                    ]
                },
            ]
        }
        xmlGenerator.createXML(
            {}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo attr1="baz">bar</foo>',
            etree.tostring(tree.getroot())
        )

    def test_generate_empty_element_with_attribute_using_var(self):
        specification = {
            '-name': "foo",
            "-attr": [
                {
                    "-name": "attr1",
                    "#content": [
                        {
                            "var": "bar"
                        }
                    ]
                }
            ]
        }

        xmlGenerator.createXML(
            {"bar": "baz"}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual('<foo attr1="baz"/>', etree.tostring(tree.getroot()))

    def test_generate_element_with_content_using_var(self):
        specification = {
            '-name': "foo",
            "#content": [
                {
                    "var": "bar"
                }
            ]
        }

        xmlGenerator.createXML(
            {"bar": "baz"}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual('<foo>baz</foo>', etree.tostring(tree.getroot()))

    def test_generate_element_with_children(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [
                        {
                            'text': 'baz'
                        }
                    ]
                }
            ]
        }

        xmlGenerator.createXML(
            {'bar': 'baz'}, {self.fname: specification}
        )

        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo>\n    <bar>baz</bar>\n</foo>',
            etree.tostring(tree.getroot())
        )

    def test_element_with_files(self):
        specification = {
            '-name': 'foo',
            '-containsFiles': [
                {
                    '-name': 'bar',
                    '-attr': [
                        {
                            '-name': 'name',
                            '#content': [
                                {
                                    'var': 'FName'
                                }
                            ]
                        }
                    ],
                    '-children': [
                        {
                            '-name': 'baz',
                            '-attr': [
                                {
                                    '-name': 'href',
                                    '#content': [
                                        {
                                            'var': 'href'
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in os.walk(self.datadir):
            for f in files:
                file_element = tree.find(".//bar[@name='%s']" % f)
                self.assertIsNotNone(file_element)

                filepath = os.path.join(root, f)
                relpath = os.path.relpath(filepath, self.datadir)

                filepath_element = tree.find(
                    ".//bar[@name='%s']/baz[@href='%s']" % (f, relpath)
                )
                self.assertIsNotNone(filepath_element)

                num_of_files += 1

        file_elements = tree.findall('.//bar')
        self.assertEqual(len(file_elements), num_of_files)

    def test_position_alphabetically(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'a',
                    '-allowEmpty': True
                },
                {
                    '-name': 'b',
                    '-allowEmpty': True
                },
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(a), root.index(b))

    def test_position_non_alphabetically(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'b',
                    '-allowEmpty': True
                },
                {
                    '-name': 'a',
                    '-allowEmpty': True
                },
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(b), root.index(a))

    def test_position_with_files(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'a',
                    '-allowEmpty': True
                },
            ],
            '-containsFiles': [
                {
                    '-name': 'b',
                    '-allowEmpty': True
                },
            ],
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(a), root.index(b))

    def test_append_element_with_namespace(self):
        PREMIS = 'http://www.loc.gov/premis/v3'

        specification = {
            '-name': 'root',
            '-attr': [
                {
                    '-name': 'xmlns:premis',
                    '#content': [
                        {
                            'text': PREMIS,
                        }
                    ]
                }
            ],
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
            '-namespace': 'premis',
            '#content': [
                {
                    'text': 'append text'
                }
            ]
        }

        for i in range(3):
            xmlGenerator.appendXML(
                {
                    'path': self.fname,
                    'elementToAppendTo': 'foo',
                    'template': append_specification,
                    'data': {},
                }
            )

        tree = etree.parse(self.fname)

        appended = tree.find('.//{%s}appended' % PREMIS)

        self.assertIsNotNone(appended)
        self.assertEqual(appended.text, 'append text')

    def test_append_nested_elements_with_namespace(self):
        PREMIS = 'http://www.loc.gov/premis/v3'

        specification = {
            '-name': 'root',
            '-attr': [
                {
                    '-name': 'xmlns:premis',
                    '#content': [
                        {
                            'text': PREMIS,
                        }
                    ]
                }
            ],
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
            '-namespace': 'premis',
            '#content': [
                {
                    'text': 'append text'
                }
            ],
            '-children': [
                {
                    '-name': 'bar',
                    '-namespace': 'premis',
                    '#content': [
                        {
                            'text': 'bar text'
                        }
                    ]
                }
            ]
        }

        for i in range(3):
            xmlGenerator.appendXML(
                {
                    'path': self.fname,
                    'elementToAppendTo': 'foo',
                    'template': append_specification,
                    'data': {},
                }
            )

        tree = etree.parse(self.fname)

        bar = tree.find('.//{%s}bar' % PREMIS)

        self.assertIsNotNone(bar)
        self.assertEqual(bar.text, 'bar text')

    def test_append_element_with_content(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
            '#content': [
                {
                    'text': 'append text'
                }
            ]
        }

        xmlGenerator.appendXML(
            {
                'path': self.fname,
                'elementToAppendTo': 'foo',
                'template': append_specification,
                'data': {},
            }
        )

        tree = etree.parse(self.fname)

        appended = tree.find('.//appended')

        self.assertIsNotNone(appended)
        self.assertEqual(appended.text, 'append text')

    def test_append_element_with_attribute(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        xmlGenerator.createXML(
            {}, {self.fname: specification}, self.datadir
        )

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
            '-attr': [
                {
                    '-name': 'bar',
                    '#content': [
                        {
                            'text': 'append text'
                        }
                    ]
                }
            ]
        }

        xmlGenerator.appendXML(
            {
                'path': self.fname,
                'elementToAppendTo': 'foo',
                'template': append_specification,
                'data': {},
            }
        )

        tree = etree.parse(self.fname)
        appended = tree.find('.//appended')

        self.assertIsNotNone(appended)
        self.assertEqual(appended.get('bar'), 'append text')


class test_parseAttribute(TestCase):
    def test_parse_attribute_only_text(self):
        attr = {
            "-name": "foo",
            "#content": [
                {
                    "text": "bar"
                },
            ]
        }

        attrobj = xmlGenerator.parseAttribute(attr, {})
        self.assertEqual(attrobj.attrName, "foo")
        self.assertEqual(attrobj.value, "bar")

    def test_parse_attribute_only_var(self):
        attr = {
            "-name": "foo",
            "#content": [
                {
                    "var": "bar"
                },
            ]
        }

        info = {
            "bar": "baz"
        }

        attrobj = xmlGenerator.parseAttribute(attr, info)
        self.assertEqual(attrobj.attrName, "foo")
        self.assertEqual(attrobj.value, "baz")

    def test_parse_attribute_var_and_text(self):
        attr = {
            "-name": "foo",
            "#content": [
                {
                    "text": "before"
                },
                {
                    "var": "bar"
                },
                {
                    "text": "after"
                },
            ]
        }

        info = {
            "bar": "baz"
        }

        attrobj = xmlGenerator.parseAttribute(attr, info)
        self.assertEqual(attrobj.attrName, "foo")
        self.assertEqual(attrobj.value, "beforebazafter")
