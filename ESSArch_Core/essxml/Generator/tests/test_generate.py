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

import datetime
import os
import re
import shutil
import tempfile
import unittest
from collections import OrderedDict
from os import walk
from unittest import mock

from django.test import TestCase
from django.utils import dateparse, timezone
from lxml import etree

from ESSArch_Core.essxml.Generator.xmlGenerator import (
    XMLGenerator,
    parseContent,
)
from ESSArch_Core.util import make_unicode, normalize_path


class GenerateXMLTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(GenerateXMLTestCase, cls).setUpClass()
        cls.generator = XMLGenerator()

    def setUp(self):
        self.bd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bd)

        self.xmldir = os.path.join(self.bd, "xmlfiles")
        self.datadir = os.path.join(self.bd, "datafiles")
        self.fname = os.path.join(self.xmldir, "test.xml")

        os.mkdir(self.xmldir)
        os.mkdir(self.datadir)
        os.makedirs(os.path.join(self.datadir, "record1"))
        os.makedirs(os.path.join(self.datadir, "record2"))

        with open(os.path.join(self.datadir, "record1/file1.txt"), 'w') as f:
            f.write('foo')

        with open(os.path.join(self.datadir, "record2/file2.txt"), 'w') as f:
            f.write('bar')

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

        self.generator.generate({self.fname: {'spec': specification, 'data': info}})

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
            self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})
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
            self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})
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
            self.generator.generate({self.fname: {'spec': specification}})

        self.assertFalse(os.path.exists(self.fname))

    def test_generate_empty_element_with_empty_attribute_with_allow_empty_on_attribute(self):
        specification = {
            '-name': 'foo',
            '-attr': [
                {
                    '-name': 'bar',
                    '#content': [{'text': ''}],
                    '-allowEmpty': True,
                },
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        root = tree.getroot()
        self.assertEqual(len(root.xpath('//foo[@bar=""]')), 1)

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual(len(tree.findall('.//bar')), 2)

    def test_generate_empty_element_with_allowEmpty(self):
        specification = {'-name': "foo", "-allowEmpty": 1}
        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot(), encoding='unicode'), "<foo/>")

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot(), encoding='unicode'), '<root>\n  <bar>baz</bar>\n</root>')

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(
            etree.tostring(tree.getroot(), encoding='unicode'),
            '<root>\n  <bar>baz</bar>\n  <foo bar="baz"/>\n</root>'
        )

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(
            etree.tostring(tree.getroot(), encoding='unicode'),
            '<root>\n  <bar>baz</bar>\n  <foo bar="baz">baz</foo>\n</root>'
        )

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot(), encoding='unicode'), '<root/>')

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

        self.generator.generate({self.fname: {'spec': specification, 'data': data}})

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//bar')

        self.assertEqual(elements[0].text, 'first')
        self.assertEqual(elements[1].text, 'second')
        self.assertEqual(elements[2].text, 'third')

    def test_generate_element_with_foreach_dict(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-foreach': 'agents',
                    '#content': [{'var': 'agents__key'}, {'text': ': '}, {'var': 'name'}],
                }
            ]
        }
        data = {
            'agents': OrderedDict([
                ('archivist_organization', {'name': 'foo'}),
                ('preservation_software', {'name': 'essarch'}),
            ])
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': data}})

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//foo')

        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].text, 'archivist_organization: foo')
        self.assertEqual(elements[1].text, 'preservation_software: essarch')

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

        self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//bar')

        self.assertEqual(len(elements), 3)
        self.assertEqual(elements[0].text, 'original_1')
        self.assertEqual(elements[1].text, 'new_2')
        self.assertEqual(elements[2].text, 'original_3')

    def test_generate_element_replace_existing_with_foreach(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'idx', '#content': [{'text': 1}]}
                    ],
                    '#content': [{'text': 'old'}]
                },
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'idx', '#content': [{'text': 3}]}
                    ],
                    '#content': [{'text': 'old'}]
                },
                {
                    '-name': "foo",
                    '-replaceExisting': ['idx'],
                    '-attr': [
                        {'-name': 'idx', '#content': [{'var': 'idx'}]}
                    ],
                    '-foreach': 'arr',
                    '#content': [{'var': 'bar'}]
                }
            ]
        }

        data = {
            'arr': [
                {'idx': 0, 'bar': 'first'},
                {'idx': 1, 'bar': 'second'},
                {'idx': 2, 'bar': 'third'},
            ]
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': data}})
        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//foo')

        self.assertEqual(len(elements), 4)
        self.assertEqual(elements[0].text, 'second')
        self.assertEqual(elements[1].text, 'old')
        self.assertEqual(elements[2].text, 'first')
        self.assertEqual(elements[3].text, 'third')

    def test_generate_element_ignore_existing_with_foreach(self):
        specification = {
            '-name': 'root',
            '-allowEmpty': True,
            '-children': [
                {
                    '-name': "foo",
                    '-attr': [
                        {'-name': 'idx', '#content': [{'text': 1}]}
                    ],
                    '#content': [{'text': 'old'}]
                },
                {
                    '-name': "foo",
                    '-ignoreExisting': ['idx'],
                    '-attr': [
                        {'-name': 'idx', '#content': [{'var': 'idx'}]}
                    ],
                    '-foreach': 'arr',
                    '#content': [{'var': 'bar'}]
                }
            ]
        }

        data = {
            'arr': [
                {'idx': 0, 'bar': 'first'},
                {'idx': 1, 'bar': 'second'},
                {'idx': 2, 'bar': 'third'},
            ]
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': data}})

        tree = etree.parse(self.fname)
        root = tree.getroot()
        elements = root.xpath('//foo')

        self.assertEqual(len(elements), 3)
        self.assertEqual(elements[0].text, 'old')
        self.assertEqual(elements[1].text, 'first')
        self.assertEqual(elements[2].text, 'third')

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot(), encoding='unicode'), '<root/>')

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

        self.generator.generate({self.fname: {'spec': specification}})
        self.assertTrue(os.path.exists(self.fname))

        tree = etree.parse(self.fname)
        self.assertEqual(etree.tostring(tree.getroot(), encoding='unicode'), '<root/>')

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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual("<foo>bar</foo>", etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_required_element_with_content(self):
        specification = {
            '-name': "foo",
            '-req': True,
            "#content": [
                {"text": "bar"}
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual("<foo>bar</foo>", etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_empty_required_element(self):
        specification = {
            '-name': "foo",
            '-req': True,
        }

        with self.assertRaises(ValueError):
            self.generator.generate({self.fname: {'spec': specification}})

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

        with self.assertRaisesRegex(ValueError, re.escape(
                "Missing value for required element '/foo[0]/bar[1]/baz[2]'")):

            self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo bar="baz"/>', etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_element_with_empty_attribute(self):
        specification = {
            '-name': "foo",
            "-attr": [{"-name": "bar"}],
            '#content': [{'text': 'baz'}],
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo>baz</foo>', etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_element_with_nameless_attribute(self):
        specification = {
            '-name': "foo",
            "-attr": [{"#content": "bar"}],
            '#content': [{'text': 'baz'}],
        }

        with self.assertRaises(ValueError):
            self.generator.generate({self.fname: {'spec': specification}})

        self.assertFalse(os.path.isfile(self.fname))

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo attr1="bar" attr2="baz"/>',
            etree.tostring(tree.getroot(), encoding='unicode')
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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo bar="baz"/>', etree.tostring(tree.getroot(), encoding='unicode'))

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

        with self.assertRaises(ValueError):
            self.generator.generate({self.fname: {'spec': specification}})

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

        with self.assertRaisesRegex(ValueError, re.escape(
                "Missing value for required attribute 'test' on element '/foo[0]/bar[1]/baz[2]'")):

            self.generator.generate({self.fname: {'spec': specification}})

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertEqual(
            '<foo attr1="baz">bar</foo>',
            etree.tostring(tree.getroot(), encoding='unicode')
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

        self.generator.generate({self.fname: {'spec': specification, 'data': {'bar': 'baz'}}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo attr1="baz"/>', etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_element_with_content_using_var(self):
        specification = {
            '-name': "foo",
            "#content": [
                {
                    "var": "bar"
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': {'bar': 'baz'}}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo>baz</foo>', etree.tostring(tree.getroot(), encoding='unicode'))

    def test_generate_element_with_nested_xml_content(self):
        specification = {
            '-name': "foo",
            '-nestedXMLContent': 'bar'
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': {'bar': '<bar>baz</bar>'}}})
        tree = etree.parse(self.fname)
        self.assertEqual('<foo>\n  <bar>baz</bar>\n</foo>', etree.tostring(tree.getroot(), encoding='unicode'))

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

        self.generator.generate({self.fname: {'spec': specification, 'data': {'bar': 'baz'}}})
        tree = etree.parse(self.fname)
        self.assertEqual(
            '<root>\n  <foo>\n    <bar>baz</bar>\n  </foo>\n</root>',
            etree.tostring(tree.getroot(), encoding='unicode')
        )

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

        self.generator.generate({self.fname: {'spec': specification, 'data': {'foo': 'baz'}}})
        tree = etree.parse(self.fname)
        self.assertEqual('<root/>', etree.tostring(tree.getroot(), encoding='unicode'))

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

        self.generator.generate({self.fname: {'spec': specification, 'data': {'bar': 'baz'}}})
        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo>\n  <bar>baz</bar>\n</foo>',
            etree.tostring(tree.getroot(), encoding='unicode')
        )

    def test_skipIfNoChildren_with_empty_child(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'first',
                    '-skipIfNoChildren': True,
                    '-attr': [
                        {'-name': 'myattr', '#content': [{'text': 'attrcontent'}]}
                    ],
                    '-children': [
                        {
                            '-name': 'bar',
                        }
                    ]
                },
                {
                    '-name': 'second',
                    '#content': [{'text': 'value'}]
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo>\n  <second>value</second>\n</foo>',
            etree.tostring(tree.getroot(), encoding='unicode')
        )

    def test_skipIfNoChildren_with_non_empty_child(self):
        specification = {
            '-name': 'foo',
            '-children': [
                {
                    '-name': 'first',
                    '-skipIfNoChildren': True,
                    '-children': [
                        {
                            '-name': 'bar',
                            '#content': [{'text': 'value'}]
                        }
                    ]
                },
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo>\n  <first>\n    <bar>value</bar>\n  </first>\n</foo>',
            etree.tostring(tree.getroot(), encoding='unicode')
        )

    def test_hide_content_if_missing_with_missing(self):
        specification = {
            "-name": "foo",
            "-allowEmpty": True,
            "-children": [
                {
                    "-name": "bar",
                    "#content": [
                        {"text": "prefix"},
                        {
                            "var": "baz",
                            "hide_content_if_missing": True
                        }
                    ]
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo/>',
            etree.tostring(tree.getroot(), encoding='unicode')
        )

    def test_hide_content_if_missing_with_not_missing(self):
        specification = {
            "-name": "foo",
            "-allowEmpty": True,
            "-children": [
                {
                    "-name": "bar",
                    "#content": [
                        {"text": "prefix"},
                        {
                            "var": "baz",
                            "hide_content_if_missing": True
                        }
                    ]
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification, 'data': {'baz': 'value'}}})
        tree = etree.parse(self.fname)

        self.assertEqual(
            '<foo>\n  <bar>prefixvalue</bar>\n</foo>',
            etree.tostring(tree.getroot(), encoding='unicode')
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
            for f in files:
                file_element = tree.find(".//bar[@name='%s']" % f)
                self.assertIsNotNone(file_element)

                filepath = os.path.join(root, f)
                relpath = normalize_path(os.path.relpath(filepath, self.datadir))
                filepath_element = tree.find(
                    ".//bar[@name='%s']/baz[@href='%s']" % (f, relpath)
                )
                self.assertIsNotNone(filepath_element)

                num_of_files += 1

        file_elements = tree.findall('.//bar')
        self.assertEqual(len(file_elements), num_of_files)

    def test_multiple_to_create_with_reference_from_second_to_first(self):
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
                            '#content': [{'var': 'FName'}]
                        }
                    ],
                    '#content': [{'var': 'href'}]
                }
            ],
        }

        os.mkdir(os.path.join(self.xmldir, 'nested'))
        first_fname = normalize_path(os.path.join(self.xmldir, 'nested', "first.xml"))
        second_fname = normalize_path(os.path.join(self.xmldir, 'nested', "second.xml"))

        self.generator.generate(
            OrderedDict([
                (first_fname, {'spec': specification}),
                (second_fname, {'spec': specification})
            ])
        )

        tree1 = etree.parse(first_fname)
        tree2 = etree.parse(second_fname)

        bars1 = tree1.findall('.//bar')
        bars2 = tree2.findall('.//bar')

        self.assertEqual(len(bars1), 0)
        self.assertEqual(len(bars2), 1)

        self.assertEqual(bars2[0].text, first_fname)

        # again, but with relpath set
        self.generator.generate(
            OrderedDict([
                (first_fname, {'spec': specification}),
                (second_fname, {'spec': specification})
            ]), relpath=self.xmldir
        )

        tree1 = etree.parse(first_fname)
        tree2 = etree.parse(second_fname)

        bars1 = tree1.findall('.//bar')
        bars2 = tree2.findall('.//bar')

        self.assertEqual(len(bars1), 0)
        self.assertEqual(len(bars2), 1)

        self.assertEqual(bars2[0].text, 'nested/first.xml')

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

        self.generator.generate(
            OrderedDict([
                (self.fname, {'spec': specification}),
                (extra_fname, {'spec': specification})
            ]), folderToParse=self.datadir
        )

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
            for f in files:
                file_element = tree.find(".//{%s}bar[@name='%s']" % (nsmap['premis'], f))
                self.assertIsNotNone(file_element)

                filepath = os.path.join(root, f)
                relpath = normalize_path(os.path.relpath(filepath, self.datadir))

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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
        tree = etree.parse(self.fname)

        num_of_files = 0

        for root, dirs, files in walk(self.datadir):
            for f in files:
                filepath = os.path.join(root, f)
                relpath = normalize_path(os.path.relpath(filepath, self.datadir))

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        self.generator.generate({self.fname: {'spec': specification}})
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)

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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

    def test_insert_from_xml_string(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        append_xml = '<appended>appended text</appended>'

        target = self.generator.find_element('foo')
        for i in range(3):
            self.generator.insert_from_xml_string(
                target, append_xml,
            )
        self.generator.write(self.fname)

        tree = etree.parse(self.fname)
        appended = tree.findall('.//appended')

        self.assertEqual(len(appended), 3)
        for i in range(3):
            self.assertEqual(appended[i].text, 'appended text')

    def test_insert_from_xml_file(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                }
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})

        append_xml = os.path.join(self.xmldir, 'append.xml')
        append_xml_string = '<appended>appended text</appended>'
        append_el = etree.fromstring(append_xml_string)
        etree.ElementTree(append_el).write(append_xml, xml_declaration=True, encoding='UTF-8')

        target = self.generator.find_element('foo')
        for i in range(3):
            self.generator.insert_from_xml_file(
                target, append_xml,
            )

        self.generator.write(self.fname)

        tree = etree.parse(self.fname)
        appended = tree.findall('.//appended')

        self.assertEqual(len(appended), 3)
        for i in range(3):
            self.assertEqual(appended[i].text, 'appended text')

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('foo')
        for i in range(3):
            self.generator.insert_from_specification(
                target, append_specification, {},
            )
        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        self.generator.insert_from_specification(
            target, append_specification, {}, index=0
        )
        self.generator.write(self.fname)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        foo = tree.find('.//foo')
        appended = tree.find('.//appended')

        self.assertLess(root.index(appended), root.index(foo))

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        self.generator.insert_from_specification(
            target, append_specification, {}, index=1
        )
        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        self.generator.insert_from_specification(
            target, append_specification, {}, before='baz'
        )
        self.generator.write(self.fname)

        tree = etree.parse(self.fname)
        root = tree.getroot()
        appended = tree.find('.//appended')
        self.assertEqual(root.index(appended), 4)

    def test_insert_element_before_non_existing_element(self):
        specification = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'foo',
                    '-allowEmpty': "1",
                },
            ]
        }

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
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

        target = self.generator.find_element('root')
        with self.assertRaises(ValueError):
            self.generator.insert_from_specification(target, append_specification, {}, before='bar')

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        self.generator.insert_from_specification(
            target, append_specification, {}, after='bar'
        )
        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        with self.assertRaises(ValueError):
            self.generator.insert_from_specification(target, append_specification, {}, after='bar')

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('root')
        with self.assertRaises(ValueError):
            self.generator.insert_from_specification(
                target, append_specification, {}, before='foo', after="foo"
            )

        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('foo')
        for i in range(3):
            self.generator.insert_from_specification(
                target, append_specification, {},
            )

        self.generator.write(self.fname)
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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('foo')
        self.generator.insert_from_specification(
            target, append_specification, {},
        )
        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
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

        target = self.generator.find_element('foo')
        self.generator.insert_from_specification(
            target, append_specification, {},
        )
        self.generator.write(self.fname)

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

        self.generator.generate({self.fname: {'spec': specification}})
        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//appended'))

        append_specification = {
            '-name': 'appended',
        }

        target = self.generator.find_element('foo')
        with self.assertRaisesRegexp(TypeError, "Can't insert"):
            self.generator.insert_from_specification(
                target, append_specification, {},
            )
        self.generator.write(self.fname)


class ExternalTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(ExternalTestCase, cls).setUpClass()
        cls.generator = XMLGenerator()

    def setUp(self):
        self.bd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bd)

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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate({self.fname: {'spec': specification}}, folderToParse=self.datadir)
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

        self.generator.generate(
            {self.fname: {'spec': specification, 'data': {'foo': 'bar'}}},
            folderToParse=self.datadir
        )
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
        self.generator.generate(
            {self.fname: {'spec': specification, 'data': {'foo': 'bar'}}},
            folderToParse=self.datadir
        )

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
        self.generator.generate(
            {
                self.fname: {
                    'spec': specification,
                    'data': {'foo': 'bar'}
                }
            },
            folderToParse=self.datadir
        )

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

    def test_parse_content_nested_var(self):
        content = [{"var": "foo.bar"}]
        info = {"foo": {"bar": "baz"}}

        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, 'baz')

    def test_parse_content_missing_var(self):
        content = [{"var": "foo"}]
        contentobj = parseContent(content, {})
        self.assertEqual(contentobj, '')

    def test_parse_content_missing_var_with_default(self):
        content = [
            {
                "var": "foo", "default": "mydefault"
            },
        ]

        contentobj = parseContent(content, {})
        self.assertEqual(contentobj, 'mydefault')

    @mock.patch('ESSArch_Core.essxml.Generator.xmlGenerator.uuid.uuid4')
    def test_parse_content_var_generate_uuid(self, mocked):
        val = 'the uuid'
        mocked.return_value = val
        content = [{"var": "_UUID"}]
        contentobj = parseContent(content, {})
        mocked.assert_called_once()
        self.assertEqual(contentobj, str(val))

    def test_parse_content_var_generate_current_time_isoformat(self):
        content = [{"var": "_NOW"}]
        contentobj = parseContent(content, {})
        dt = dateparse.parse_datetime(contentobj)
        iso = dt.isoformat()
        self.assertEqual(contentobj, iso)
        self.assertEqual(dt.utcoffset(), datetime.timedelta(0))

    def test_parse_content_var_datetime_to_date(self):
        val = timezone.now()
        content = [{"var": "foo__DATE"}]
        contentobj = parseContent(content, {'foo': val})
        self.assertEqual(contentobj, val.strftime('%Y-%m-%d'))

    def test_parse_content_var_datetime_to_local_timezone(self):
        val = timezone.now()
        content = [{"var": "foo__LOCALTIME"}]
        contentobj = parseContent(content, {'foo': val})
        dt = dateparse.parse_datetime(contentobj)
        self.assertEqual(dt, timezone.localtime(val))

    def test_parse_django_template(self):
        contentobj = parseContent("hello {{foo}}", {"foo": "world"})
        self.assertEqual(contentobj, 'hello world')

        val = timezone.now()
        content = "{% load tz %}{{foo | date:'c'}}"
        contentobj = parseContent(content, {'foo': val})
        dt = dateparse.parse_datetime(contentobj)
        self.assertEqual(str(dt), str(timezone.localtime(val)))

    def test_parse_django_template_with_leading_underscore(self):
        contentobj = parseContent("{{_foo}} {{bar_foo}}", {"_foo": "hello", "bar_foo": "world"})
        self.assertEqual(contentobj, 'hello world')

        contentobj = parseContent("hello {{_foo}}", {"_foo": "world"})
        self.assertEqual(contentobj, 'hello world')

        contentobj = parseContent("{{_bar}} {{_foo}}", {"bar": "hello", "_foo": "world"})
        self.assertEqual(contentobj, 'hello world')

        contentobj = parseContent("{{_bar}} {{_foo}}", {"_bar": "hello", "_foo": "world", "foo": "world"})
        self.assertEqual(contentobj, 'hello world')

    def test_unicode(self):
        content = [{"var": "foo"}]
        foo = "åäö"
        info = {"foo": foo}
        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, make_unicode(foo))

        content = [{"var": "bar"}]
        bar = make_unicode("åäö")
        info = {"bar": bar}
        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, bar)

        content = [{"var": "foo"}, {"var": "bar"}]
        info = {"foo": foo, "bar": bar}
        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, make_unicode(foo) + bar)

        # django template system
        contentobj = parseContent("{{foo}}", {"foo": "åäö"})
        self.assertEqual(contentobj, u"åäö")

    def test_iso_8859(self):
        from ESSArch_Core.essxml.Generator.xmlGenerator import parse_content_django
        content = [{"var": "foo"}]
        foo = u"åäö".encode("iso-8859-1")
        info = {"foo": foo}
        contentobj = parseContent(content, info)
        self.assertEqual(contentobj, u"åäö")

        # django template system
        foo = "åäö".encode("iso-8859-1")
        info = {"foo": foo}
        contentobj = parse_content_django("{{foo}}", info)
        self.assertEqual(contentobj, "åäö")
