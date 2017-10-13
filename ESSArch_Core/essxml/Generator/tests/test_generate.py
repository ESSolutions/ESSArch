# -*- coding: utf-8 -*-
"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import mock
import os
import shutil
import unittest
from collections import OrderedDict

from django.test import TestCase

from lxml import etree

from scandir import walk

from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator, parseContent

from ESSArch_Core.configuration.models import (
    Path,
)


class GenerateXMLTestCase(TestCase):
    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        self.xmldir = os.path.join(self.bd, "xmlfiles")
        self.datadir = os.path.join(self.bd, "datafiles")
        self.fname = os.path.join(self.xmldir, "test.xml")

        os.mkdir(self.xmldir)
        os.mkdir(self.datadir)
        os.makedirs(os.path.join(self.datadir, "record1"))
        os.makedirs(os.path.join(self.datadir, "record2"))

        open(os.path.join(self.datadir, "record1/file1.txt"), "a").close()
        open(os.path.join(self.datadir, "record2/file2.txt"), "a").close()

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.bd, "mime.types")
        )

        patcher = mock.patch('ESSArch_Core.essxml.Generator.xmlGenerator.FormatIdentifier')
        self.addCleanup(patcher.stop)
        self.mock_fid = patcher.start()
        self.mock_fid().identify_file_format.return_value = ('name', 'version', 'reg_key')

    def tearDown(self):
        try:
            shutil.rmtree(self.xmldir)
        except:
            pass

        try:
            shutil.rmtree(self.datadir)
        except:
            pass

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
                    "#content": [{"var": "xsi:schemaLocation"}]
                },
            ]
        }

        info = {
            "xsi:schemaLocation": "http://www.w3.org/1999/xlink schemas/xlink.xsd",
        }

        generator = XMLGenerator({self.fname: {'spec': specification, 'data': info}})
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
                {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
                {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
                {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual(len(tree.findall('.//bar')), 2)

    def test_generate_empty_element_with_allowEmpty(self):
        specification = {'-name': "foo", "-allowEmpty": 1}

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), "<foo/>")

    def test_generate_empty_element_with_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "bar",
                    "#content": [{"text": "baz"}]
                },
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    "-attr": [
                        {
                            "-name": "bar",
                            "#content": [{"text": "baz"}]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root>\n  <bar>baz</bar>\n</root>')

    def test_generate_empty_element_without_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "bar",
                    "#content": [{"text": "baz"}]
                },
                {
                    '-name': "foo",
                    "-attr": [
                        {
                            "-name": "bar",
                            "#content": [{"text": "baz"}]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root>\n  <bar>baz</bar>\n  <foo bar="baz"/>\n</root>')

    def test_generate_element_with_content_and_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "bar",
                    "#content": [{"text": "baz"}]
                },
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    "#content": [{"text": "baz"}],
                    "-attr": [
                        {
                            "-name": "bar",
                            "#content": [{"text": "baz"}]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root>\n  <bar>baz</bar>\n  <foo bar="baz">baz</foo>\n</root>')

    def test_generate_element_with_empty_child_and_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    '-children': [
                        {
                            '-name': "bar",
                        },
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root/>')

    def test_generate_element_with_foreach(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-foreach': 'arr',
                    '-children': [
                        {
                            '-name': "bar",
                            '#content': [{'var': 'bar'}],
                        },
                    ]
                }
            ]
        }

        data = {
            'arr': [
                {'bar': 'first'},
                {'bar': 'second'},
                {'bar': 'third'},
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': data}}
        )
        generator.generate()

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//bar')

        self.assertEqual(elements[0].text, 'first')
        self.assertEqual(elements[1].text, 'second')
        self.assertEqual(elements[2].text, 'third')

    def test_generate_element_replace_existing(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]}
                    ],
                    '#content': [{'text': 'old'}]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['type'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]}
                    ],
                    '#content': [{'text': 'new'}]
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )
        generator.generate()

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//foo')

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].text, 'new')

    def test_generate_element_replace_existing_multiple_attributes(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]},
                        {'-name': 'role', '#content': [{'text': 'foo'}]}
                    ],
                    '#content': [{'text': 'old'}]
                },
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]},
                        {'-name': 'role', '#content': [{'text': 'bar'}]}
                    ],
                    '#content': [{'text': 'old 2'}]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['type', 'role'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]},
                        {'-name': 'role', '#content': [{'text': 'foo'}]}
                    ],
                    '#content': [{'text': 'new'}]
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )
        generator.generate()

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//foo')

        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].text, 'new')
        self.assertEqual(elements[1].text, 'old 2')

    def test_generate_element_replace_existing_index(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "foo",
                    '-replaceExisting': ['type'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '1'}]}
                    ],
                    '-children': [
                        {
                            '-name': "bar",
                            '#content': [{'text': 'original_1'}],
                        },
                    ]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['type'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '2'}]}
                    ],
                    '-children': [
                        {
                            '-name': "bar",
                            '#content': [{'text': 'original_2'}],
                        },
                    ]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['type'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '3'}]}
                    ],
                    '-children': [
                        {
                            '-name': "bar",
                            '#content': [{'text': 'original_3'}],
                        },
                    ]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['type'],
                    '-attr': [
                        {'-name': 'type', '#content': [{'text': '2'}]}
                    ],
                    '-children': [
                        {
                            '-name': "bar",
                            '#content': [{'text': 'new_2'}],
                        },
                    ]
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )
        generator.generate()

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//bar')

        self.assertEqual(len(elements), 3)
        self.assertEqual(elements[0].text, 'original_1')
        self.assertEqual(elements[1].text, 'new_2')
        self.assertEqual(elements[2].text, 'original_3')

    def test_generate_element_with_empty_child_with_containsFiles_and_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    '-children': [
                        {
                            '-name': "bar",
                            '-containsFiles': True,
                        },
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root/>')

    def test_generate_element_with_empty_child_with_containsFiles_and_hideEmptyContent_and_attributes(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    "-attr": [
                        {
                            "-name": "ID",
                            "#content": [{"text": "ID"}]
                        }
                    ],
                    '-children': [
                        {
                            '-name': "bar",
                            '-hideEmptyContent': True,
                            "-attr": [
                                {
                                    "-name": "ID",
                                    "#content": [{"text": "ID"}]
                                }
                            ],
                        },
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot()), '<root/>')

    def test_generate_element_with_empty_child_with_containsFiles_and_files_and_hideEmptyContent(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-hideEmptyContent': True,
                    '-children': [
                        {
                            '-name': "bar",
                            '-containsFiles': True,
                            '-attr': [
                                {
                                    '-name': 'name',
                                    '#content': [{'var': 'FName'}]
                                }
                            ]
                        },
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
            for f in files:
                file_element = tree.find(".//bar[@name='%s']" % f)
                self.assertIsNotNone(file_element)

                num_of_files += 1

        file_elements = tree.findall('.//bar')
        self.assertEqual(len(file_elements), num_of_files)

    def test_generate_element_with_content(self):
        specification = {
            '-name': "foo",
            "#content": [
                {"text": "bar"}
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual("<foo>bar</foo>", etree.tostring(tree.getroot()))

    def test_generate_required_element_with_content(self):
        specification = {
            '-name': "foo",
            '-req': True,
            "#content": [
                {"text": "bar"}
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual("<foo>bar</foo>", etree.tostring(tree.getroot()))

    def test_generate_empty_required_element(self):
        specification = {
            '-name': "foo",
            '-req': True,
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        with self.assertRaises(ValueError):
            generator.generate()

        self.assertFalse(os.path.exists(self.fname))

    def test_generate_nested_empty_required_element(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [{'text': 'baz'}],
                },
                {
                    '-name': 'bar',
                    '-children': [
                        {
                            '-name': 'baz',
                            '#content': [{'text': 'first'}],
                        },
                        {
                            '-name': 'baz',
                            '#content': [{'text': 'second'}],
                        },
                        {
                            '-name': 'baz',
                            '-req': True,
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        with self.assertRaises(ValueError) as e:
            generator.generate()

        self.assertEqual(e.exception.message, "Missing value for required element '/foo[0]/bar[1]/baz[2]'")
        self.assertFalse(os.path.exists(self.fname))

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
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo attr1="bar" attr2="baz"/>',
            etree.tostring(tree.getroot())
        )

    def test_generate_required_attribute_with_content(self):
        specification = {
            '-name': "foo",
            "-attr": [
                {
                    "-name": "bar",
                    "-req": True,
                    "#content": [
                        {
                            "text": "baz"
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual('<foo bar="baz"/>', etree.tostring(tree.getroot()))

    def test_generate_empty_required_attribute(self):
        specification = {
            '-name': "foo",
            "-attr": [
                {
                    "-name": "bar",
                    "-req": True,
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        with self.assertRaises(ValueError):
            generator.generate()

        self.assertFalse(os.path.exists(self.fname))

    def test_generate_nested_empty_required_attribute(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [{'text': 'baz'}],
                },
                {
                    '-name': 'bar',
                    '-children': [
                        {
                            '-name': 'baz',
                            '#content': [{'text': 'first'}],
                        },
                        {
                            '-name': 'baz',
                            '#content': [{'text': 'second'}],
                        },
                        {
                            '-name': 'baz',
                            "-attr": [
                                {
                                    "-name": "test",
                                    "-req": True,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        with self.assertRaises(ValueError) as e:
            generator.generate()

        self.assertEqual(e.exception.message, "Missing value for required attribute 'test' on element '/foo[0]/bar[1]/baz[2]'")
        self.assertFalse(os.path.exists(self.fname))

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
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification, 'data': {'bar': 'baz'}}}
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
            {self.fname: {'spec': specification, 'data': {'bar': 'baz'}}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual('<foo>baz</foo>', etree.tostring(tree.getroot()))

    def test_generate_element_with_requiredParameters_and_required_var(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': "foo",
                    '-requiredParameters': ['bar'],
                    '-children': [
                        {
                            '-name': 'bar',
                            "#content": [
                                {
                                    "var": "bar"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': {'bar': 'baz'}}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual('<root>\n  <foo>\n    <bar>baz</bar>\n  </foo>\n</root>', etree.tostring(tree.getroot()))

    def test_generate_element_with_requiredParameters_and_no_required_var(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-requiredParameters': ['bar'],
                    '-children': [
                        {
                            '-name': 'bar',
                            "#content": [
                                {
                                    "var": "bar"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': {'foo': 'baz'}}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertEqual('<root/>', etree.tostring(tree.getroot()))

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
            {self.fname: {'spec': specification, 'data': {'bar': 'baz'}}}
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
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
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

    def test_multiple_to_create_with_files(self):
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

        extra_fname = os.path.join(self.xmldir, "extra.xml")

        generator = XMLGenerator(
            OrderedDict([
                (self.fname, {'spec': specification}),
                (extra_fname, {'spec': specification})
            ])
        )

        generator.generate(folderToParse=self.datadir)

        tree1 = etree.parse(self.fname)
        tree2 = etree.parse(extra_fname)

        bars1 = tree1.findall('.//bar')
        bars2 = tree2.findall('.//bar')

        self.assertTrue(len(bars2) == len(bars1) + 1)

    def test_element_with_containsFiles_without_files(self):
        specification = {
            '-name': 'foo',
            '-allowEmpty': True,
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
                }
            ],
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        self.assertTrue(os.path.exists(self.fname))

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
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
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
                    "-filters": {"href": "record1/*"},
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
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
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
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
                    "-filters": {"href": "record1/*"},
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
            {self.fname: {'spec': specification}}
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
                    "-filters": {"href": "record1/*"},
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
                    "-filters": {"href": "record2/*"},
                },
                {
                    '-name': 'e',
                    '-allowEmpty': True
                },
            ],
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

    def test_insert_element_with_namespace(self):
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
            {self.fname: {'spec': specification}}
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
            generator.insert(
                self.fname, 'foo', append_specification, {},
            )

        tree = etree.parse(self.fname)

        appended = tree.find('.//{%s}appended' % nsmap.get('premis'))

        self.assertIsNotNone(appended)
        self.assertEqual(appended.text, 'append text')

    def test_insert_element_at_index(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'bar',
                    '-allowEmpty': "1",
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'root', append_specification, {}, index=0
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        foo = tree.find('.//foo')
        appended = tree.find('.//appended')

        self.assertLess(root.index(appended), root.index(foo))

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'root', append_specification, {}, index=1
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        foo = tree.find('.//foo')
        appended = tree.find('.//appended')

        self.assertLess(root.index(foo), root.index(appended))

    def test_insert_element_before_element(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'bar',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'bar',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'baz',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'baz',
                    '-allowEmpty': "1",
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'root', append_specification, {}, before='baz'
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        appended = tree.find('.//appended')
        self.assertEqual(root.index(appended), 4)

    def test_insert_element_after_element(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'bar',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'bar',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'baz',
                    '-allowEmpty': "1",
                },
                {
                    '-name': 'baz',
                    '-allowEmpty': "1",
                }
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'root', append_specification, {}, after='bar'
        )

        tree = etree.parse(self.fname)
        root = tree.getroot()
        appended = tree.find('.//appended')
        self.assertEqual(root.index(appended), 4)

    def test_insert_element_after_non_existing_element(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
            ]
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
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

        with self.assertRaises(ValueError):
            generator.insert(self.fname, 'root', append_specification, {}, after='bar')

    def test_insert_element_before_and_after_element(self):
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
            {self.fname: {'spec': specification}}
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

        with self.assertRaises(ValueError):
            generator.insert(
                self.fname, 'root', append_specification, {}, before='foo', after="foo"
            )

    def test_insert_nested_elements_with_namespace(self):
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
            {self.fname: {'spec': specification}}
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
            generator.insert(
                self.fname, 'foo', append_specification, {},
            )

        tree = etree.parse(self.fname)

        bar = tree.find('.//{%s}bar' % nsmap.get('premis'))

        self.assertIsNotNone(bar)
        self.assertEqual(bar.text, 'bar text')

    def test_insert_element_with_content(self):
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
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'foo', append_specification, {},
        )

        tree = etree.parse(self.fname)

        appended = tree.find('.//appended')

        self.assertIsNotNone(appended)
        self.assertEqual(appended.text, 'append text')

    def test_insert_element_with_attribute(self):
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
            {self.fname: {'spec': specification}}
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

        generator.insert(
            self.fname, 'foo', append_specification, {},
        )

        tree = etree.parse(self.fname)
        appended = tree.find('.//appended')

        self.assertIsNotNone(appended)
        self.assertEqual(appended.get('bar'), 'append text')

    def test_insert_empty_element(self):
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
            {self.fname: {'spec': specification}}
        )

        generator.generate()

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
        }

        with self.assertRaisesRegexp(TypeError, "Can't insert"):
            generator.insert(
                self.fname, 'foo', append_specification, {},
            )


class ExternalTestCase(TestCase):
    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        self.xmldir = os.path.join(self.bd, "xmlfiles")
        self.datadir = os.path.join(self.bd, "datafiles")
        self.external = os.path.join(self.datadir, "external")
        self.fname = os.path.join(self.xmldir, "test.xml")

        os.mkdir(self.xmldir)
        os.mkdir(self.datadir)
        os.mkdir(self.external)

        self.external1 = os.path.join(self.external, "external1")
        self.external2 = os.path.join(self.external, "external2")
        os.makedirs(self.external1)
        os.makedirs(self.external2)

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.bd, "mime.types")
        )

        patcher = mock.patch('ESSArch_Core.essxml.Generator.xmlGenerator.FormatIdentifier')
        self.addCleanup(patcher.stop)
        self.mock_fid = patcher.start()
        self.mock_fid().identify_file_format.return_value = ('name', 'version', 'reg_key')

    def tearDown(self):
        try:
            shutil.rmtree(self.xmldir)
        except:
            pass

        try:
            shutil.rmtree(self.datadir)
        except:
            pass

        try:
            os.remove(self.fname)
        except:
            pass

    def test_external(self):
        specification = {
            '-name': 'root',
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '#content': [{'var': '_EXT_HREF'}]
                },
                '-specification': {
                    '-name': 'extroot',
                    '-children': [
                        {
                            '-name': 'foo',
                            '#content': [{'var': '_EXT'}]
                        }
                    ]
                }
            },
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        self.assertTrue(os.path.isfile(self.fname))

        external1_path = os.path.join(self.external1, 'external.xml')
        external2_path = os.path.join(self.external2, 'external.xml')

        tree = etree.parse(self.fname)

        self.assertEqual(len(tree.xpath(".//ptr[text()='%s']" % os.path.relpath(external1_path, self.datadir))), 1)
        self.assertEqual(len(tree.xpath(".//ptr[text()='%s']" % os.path.relpath(external2_path, self.datadir))), 1)

        self.assertTrue(os.path.isfile(external1_path))
        self.assertTrue(os.path.isfile(external2_path))

        external1_tree = etree.parse(external1_path)
        self.assertEqual(len(external1_tree.xpath(".//foo[text()='external1']")), 1)

        external2_tree = etree.parse(external2_path)
        self.assertEqual(len(external2_tree.xpath(".//foo[text()='external2']")), 1)

    def test_external_with_files(self):
        specification = {
            '-name': 'root',
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': '_EXT_HREF'}]
                        },
                    ],
                },
                '-specification': {
                    '-name': 'mets',
                    '-attr': [
                        {
                            '-name': 'LABEL',
                            '#content': [{'var': '_EXT'}]
                        },
                    ],
                    '-children': [
                        {
                            '-name': 'file',
                            '-containsFiles': True,
                            '-attr': [
                                {
                                    '-name': 'href',
                                    '#content': [{'var': 'href'}]
                                },
                            ],
                        },
                    ]
                }
            },
        }

        with open(os.path.join(self.external1, "file1.txt"), "w") as f:
            f.write('a txt file')
        with open(os.path.join(self.external2, "file1.pdf"), "w") as f:
            f.write('a pdf file')

        generator = XMLGenerator(
            {self.fname: {'spec': specification}}
        )

        generator.generate(folderToParse=self.datadir)

        self.assertTrue(os.path.isfile(self.fname))

        tree = etree.parse(self.fname)

        external1_path = os.path.join(self.external1, 'external.xml')
        external2_path = os.path.join(self.external2, 'external.xml')

        self.assertIsNone(tree.find('.//file'))

        self.assertEqual(len(tree.findall(".//ptr[@href='%s']" % os.path.relpath(external1_path, self.datadir))), 1)
        self.assertEqual(len(tree.findall(".//ptr[@href='%s']" % os.path.relpath(external2_path, self.datadir))), 1)

        self.assertTrue(os.path.isfile(external1_path))
        self.assertTrue(os.path.isfile(external2_path))

        external1_tree = etree.parse(external1_path)
        self.assertEqual(len(external1_tree.findall(".//file[@href='file1.txt']")), 1)

        external2_tree = etree.parse(external2_path)
        self.assertEqual(len(external2_tree.findall(".//file[@href='file1.pdf']")), 1)

    def test_external_info(self):
        specification = {
            '-name': 'root',
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': '_EXT_HREF'}]
                        },
                    ],
                },
                '-specification': {
                    '-name': 'extroot',
                    '-children': [
                        {
                            '-name': 'foo',
                            '#content': [{'var': 'foo'}]
                        }
                    ]
                }
            },
        }

        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': {'foo': 'bar'}}},
        )

        generator.generate(folderToParse=self.datadir)

        self.assertTrue(os.path.isfile(self.fname))

        external1_path = os.path.join(self.external1, 'external.xml')
        external2_path = os.path.join(self.external2, 'external.xml')

        external1_tree = etree.parse(external1_path)
        self.assertEqual(len(external1_tree.xpath('.//foo[text()="bar"]')), 1)

        external2_tree = etree.parse(external2_path)
        self.assertEqual(len(external2_tree.xpath(".//foo[text()='bar']")), 1)

    def test_external_nsmap(self):
        nsmap = {
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        specification = {
            '-name': 'root',
            '-nsmap': nsmap,
            '-namespace': 'xsi',
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': '_EXT_HREF'}]
                        },
                    ],
                },
                '-specification': {
                    '-name': 'extroot',
                    '-children': [
                        {
                            '-name': 'foo',
                            '-namespace': 'xsi',
                            '#content': [{'text': 'bar'}]
                        }
                    ]
                }
            },
        }
        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': {'foo': 'bar'}}},
        )
        generator.generate(folderToParse=self.datadir)

        external1_path = os.path.join(self.external1, 'external.xml')
        external2_path = os.path.join(self.external2, 'external.xml')

        external1_tree = etree.parse(external1_path)
        self.assertIsNotNone(external1_tree.find('.//xsi:foo', namespaces=nsmap))

        external2_tree = etree.parse(external2_path)
        self.assertIsNotNone(external2_tree.find('.//xsi:foo', namespaces=nsmap))

    def test_external_nsmap_collision(self):
        nsmap = {
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        nsmap_ext = {
            'xsi': 'external_xsi',
        }

        specification = {
            '-name': 'root',
            '-nsmap': nsmap,
            '-namespace': 'xsi',
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': '_EXT_HREF'}]
                        },
                    ],
                },
                '-specification': {
                    '-name': 'extroot',
                    '-nsmap': nsmap_ext,
                    '-children': [
                        {
                            '-name': 'foo',
                            '-namespace': 'xsi',
                            '#content': [{'text': 'bar'}]
                        }
                    ]
                }
            },
        }
        generator = XMLGenerator(
            {self.fname: {'spec': specification, 'data': {'foo': 'bar'}}},
        )
        generator.generate(folderToParse=self.datadir)

        external1_path = os.path.join(self.external1, 'external.xml')
        external2_path = os.path.join(self.external2, 'external.xml')

        external1_tree = etree.parse(external1_path)
        self.assertIsNotNone(external1_tree.find('.//xsi:foo', namespaces=nsmap_ext))

        external2_tree = etree.parse(external2_path)
        self.assertIsNotNone(external2_tree.find('.//xsi:foo', namespaces=nsmap_ext))


class ParseContentTestCase(unittest.TestCase):
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

    def test_parse_content_only_var_integer(self):
        content = [
            {
                "var": "foo"
            },
        ]

        info = {
            "foo": 0
        }

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, '0')

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

    def test_parse_content_var_with_default(self):
        content = [
            {
                "var": "foo", "default": "mydefault"
            },
        ]

        info = {
            "foo": "bar"
        }

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, 'bar')

    def test_parse_content_missing_var_with_default(self):
        content = [
            {
                "var": "foo", "default": "mydefault"
            },
        ]

        contentobj = parseContent(content, {})
        self.assertEqual(contentobj, 'mydefault')

    def test_unicode(self):
        content = [{"var": "foo"}]
        foo = unicode("åäö", 'utf-8')
        info = {"foo": foo}

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, foo)
