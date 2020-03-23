import os
import shutil
import sqlite3
import tempfile
from unittest import mock

from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.fixity.conversion.backends.siard import SiardConverter


class SiardConverterTests(SimpleTestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_convert(self):
        converter = SiardConverter()
        shutil.copy2(os.path.join(os.path.dirname(__file__), 'sfdboe.siard'), self.datadir)
        converter.convert(os.path.join(self.datadir, 'sfdboe.siard'))
        self.assertCountEqual(os.listdir(self.datadir), ['HR.sqlite', 'MDSYS.sqlite', 'OE.sqlite', 'sfdboe.siard'])

        with self.subTest('HR.sqlite'):
            db = sqlite3.connect(os.path.join(self.datadir, 'HR.sqlite'))
            cursor = db.cursor()

            cursor.row_factory = lambda cursor, row: row[0]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            expected_tables = [
                'COUNTRIES',
                'DEPARTMENTS',
                'EMPLOYEES',
                'JOBS',
                'JOB_HISTORY',
                'LOCATIONS',
            ]
            self.assertCountEqual(tables, expected_tables)
            cursor.close()
            db.close()

        with self.subTest('MDSYS.sqlite'):
            db = sqlite3.connect(os.path.join(self.datadir, 'MDSYS.sqlite'))
            cursor = db.cursor()

            cursor.row_factory = lambda cursor, row: row[0]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            expected_tables = []
            self.assertCountEqual(tables, expected_tables)
            cursor.close()
            db.close()

        with self.subTest('OE.sqlite'):
            db = sqlite3.connect(os.path.join(self.datadir, 'OE.sqlite'))
            cursor = db.cursor()

            cursor.row_factory = lambda cursor, row: row[0]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            expected_tables = [
                'CUSTOMERS',
                'INVENTORIES',
                'ORDERS',
                'ORDER_ITEMS',
                'PRODUCT_DESCRIPTIONS',
                'PRODUCT_INFORMATION',
                'PROMOTIONS',
                'WAREHOUSES',
            ]
            self.assertCountEqual(tables, expected_tables)
            cursor.close()
            db.close()

    @mock.patch('ESSArch_Core.fixity.conversion.backends.siard.SiardConverter.convert')
    def test_cli(self, mock_convert):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo.siard', 'a').close()

            result = runner.invoke(SiardConverter.cli, ['foo.siard'])
            mock_convert.assert_called_once_with('foo.siard')

            self.assertEqual(result.exit_code, 0)
