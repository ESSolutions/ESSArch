import os, shutil

from django.test import TestCase

from lxml import etree

from demo.xmlGenerator import XMLGenerator, parseContent

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
        nsmap = {
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        specification = {
            "-name": "foo",
            '-nsmap': nsmap,
            "-attr": [
                {
                    "-name": "schemaLocation",
                    "-namespace": "xsi",
                    "-req": 1,
                    "#content": [{"var":"xsi:schemaLocation"}]
                },
            ]
        }

        info = {
            "xsi:schemaLocation": "http://www.w3.org/1999/xlink schemas/xlink.xsd",
        }

        generator = XMLGenerator(
            {self.fname: specification}, info
        )

        generator.generate()

        tree = etree.parse(self.fname)
        root = tree.getroot()

        xsi_ns = root.nsmap.get("xsi")

        self.assertEqual(xsi_ns, nsmap.get("xsi"))
        self.assertEqual(
            root.attrib.get("{%s}schemaLocation" % xsi_ns),
            info["xsi:schemaLocation"]
        )

    def test_generate_empty_element(self):
        specification = {'-name': "foo"}

        with self.assertRaises(AssertionError):
            generator = XMLGenerator(
                {self.fname: specification}, {}
            )

            generator.generate()

        self.assertFalse(os.path.exists(self.fname))

    def test_generate_empty_element_with_children(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [{
                        'text': 'baz'
                    }]
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: specification}, {}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

    def test_generate_empty_element_with_empty_children(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                },
            ]
        }

        with self.assertRaises(AssertionError):
            generator = XMLGenerator(
                {self.fname: specification}, {}
            )

            generator.generate()

        self.assertFalse(os.path.exists(self.fname))

    def test_generate_empty_element_with_empty_children_with_allow_empty(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '-allowEmpty': True
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: specification}, {}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

    def test_generate_empty_element_with_empty_attribute(self):
        specification = {
            '-name': 'foo',
            '-attr': [
                {
                    '-name': 'bar',
                    '#content': [{
                        'text': ''
                    }]
                },
            ]
        }

        with self.assertRaises(AssertionError):
            generator = XMLGenerator(
                {self.fname: specification}, {}
            )

            generator.generate()

        self.assertFalse(os.path.exists(self.fname))

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

        generator = XMLGenerator(
            {self.fname: specification}, {}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual(len(tree.findall('.//bar')), 2)

    def test_generate_empty_element_with_allowEmpty(self):
        specification = {'-name': "foo", "-allowEmpty": 1}

        generator = XMLGenerator(
            {self.fname: specification}, {}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}, {'bar': 'baz'}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}, {'bar': 'baz'}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}, {'bar': 'baz'}
        )

        generator.generate()

        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo>\n  <bar>baz</bar>\n</foo>',
            etree.tostring(tree.getroot())
        )

    def test_element_with_files(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '-containsFiles': True,
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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(folderToParse=self.datadir)

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

    def test_element_with_files_and_namespace(self):
        nsmap = {
            'premis': 'http://www.loc.gov/premis/v3'
        }

        specification = {
            '-name': 'foo',
            '-nsmap': nsmap,
            '-children': [
                {
                    '-name': 'bar',
                    '-namespace': 'premis',
                    '-containsFiles': True,
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
                            '-namespace': 'premis',
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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(folderToParse=self.datadir)

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in os.walk(self.datadir):
            for f in files:
                file_element = tree.find(".//{%s}bar[@name='%s']" % (nsmap['premis'], f))
                self.assertIsNotNone(file_element)

                filepath = os.path.join(root, f)
                relpath = os.path.relpath(filepath, self.datadir)

                filepath_element = tree.find(
                    ".//{%s}bar[@name='%s']/{%s}baz[@href='%s']" % (nsmap['premis'], f, nsmap['premis'], relpath)
                )
                self.assertIsNotNone(filepath_element)

                num_of_files += 1

        file_elements = tree.findall('.//{%s}bar' % nsmap['premis'])
        self.assertEqual(len(file_elements), num_of_files)

    def test_element_with_filtered_files(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '-containsFiles': True,
                    "-filters": {"href":"record1/*"},
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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(folderToParse=self.datadir)

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in os.walk(self.datadir):
            for f in files:
                filepath = os.path.join(root, f)
                relpath = os.path.relpath(filepath, self.datadir)

                filepath_element = tree.find(
                    ".//bar[@name='%s']/baz[@href='%s']" % (f, relpath)
                )

                if relpath.startswith('record1'):
                    self.assertIsNotNone(filepath_element)
                    num_of_files += 1
                else:
                    self.assertIsNone(filepath_element)


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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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
                {
                    '-name': 'b',
                    '-containsFiles': True,
                    '#content': [{
                        'var': 'href'
                    }],
                    "-filters": {"href":"record1/*"},
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(self.datadir)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(a), root.index(b))

        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'b',
                    '-containsFiles': True,
                },
                {
                    '-name': 'a',
                    '-allowEmpty': True
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(self.datadir)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(b), root.index(a))

        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'a',
                    '-containsFiles': True,
                },
                {
                    '-name': 'b',
                    '-allowEmpty': True
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(self.datadir)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(a), root.index(b))

        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'b',
                    '-allowEmpty': True
                },
                {
                    '-name': 'a',
                    '-containsFiles': True,
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(self.datadir)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')

        self.assertLess(root.index(b), root.index(a))

        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'a',
                    '-allowEmpty': True
                },
                {
                    '-name': 'b',
                    '-containsFiles': True,
                    '#content': [{
                        'var': 'href'
                    }],
                    "-filters": {"href":"record1/*"},
                },
                {
                    '-name': 'c',
                    '-allowEmpty': True
                },
                {
                    '-name': 'd',
                    '-containsFiles': True,
                    '#content': [{
                        'var': 'href'
                    }],
                    "-filters": {"href":"record2/*"},
                },
                {
                    '-name': 'e',
                    '-allowEmpty': True
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate(self.datadir)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        a = root.find('.//a')
        b = root.find('.//b')
        c = root.find('.//c')
        d = root.find('.//d')
        e = root.find('.//e')

        self.assertLess(root.index(a), root.index(b))
        self.assertLess(root.index(b), root.index(c))
        self.assertLess(root.index(c), root.index(d))
        self.assertLess(root.index(d), root.index(e))

    def test_append_element_with_namespace(self):
        nsmap = {
            'premis': 'http://www.loc.gov/premis/v3'
        }

        specification = {
            '-name': 'root',
            '-nsmap': nsmap,
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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
            generator.append(
                self.fname, 'foo', append_specification, {},
            )

        tree = etree.parse(self.fname)

        appended = tree.find('.//{%s}appended' % nsmap.get('premis'))

        self.assertIsNotNone(appended)
        self.assertEqual(appended.text, 'append text')

    def test_append_nested_elements_with_namespace(self):
        nsmap = {
            'premis': 'http://www.loc.gov/premis/v3'
        }

        specification = {
            '-name': 'root',
            '-nsmap': nsmap,
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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
            generator.append(
                self.fname, 'foo', append_specification, {},
            )

        tree = etree.parse(self.fname)

        bar = tree.find('.//{%s}bar' % nsmap.get('premis'))

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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator.append(
            self.fname, 'foo', append_specification, {},
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

        generator = XMLGenerator(
            {self.fname: specification}
        )

        generator.generate()

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

        generator.append(
            self.fname, 'foo', append_specification, {},
        )

        tree = etree.parse(self.fname)
        appended = tree.find('.//appended')

        self.assertIsNotNone(appended)
        self.assertEqual(appended.get('bar'), 'append text')


class test_parseContent(TestCase):
    def test_parse_content_only_text(self):
        content = [
            {
                "text": "bar"
            },
        ]

        contentobj = parseContent(content, {})
        self.assertEqual(contentobj, 'bar')

    def test_parse_content_only_var(self):
        content = [
            {
                "var": "foo"
            },
        ]

        info = {
            "foo": "bar"
        }

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, 'bar')

    def test_parse_content_var_and_text(self):
        content = [
            {
                "text": "before"
            },
            {
                "var": "foo"
            },
            {
                "text": "after"
            },
        ]

        info = {
            "foo": "bar"
        }

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, 'beforebarafter')
