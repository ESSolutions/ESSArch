import json
import logging
import os
import sqlite3
import zipfile

import click
from lxml import etree

from ESSArch_Core.fixity.conversion.backends.base import BaseConverter

mappings = {
    'INT': 'INTEGER',
    'INTEGER': 'INTEGER',
    'TINYINT': 'INTEGER',
    'SMALLINT': 'INTEGER',
    'MEDIUMINT': 'INTEGER',
    'BIGINT': 'INTEGER',
    'UNSIGNED BIG INT': 'INTEGER',
    'INT2': 'INTEGER',
    'INT8': 'INTEGER',
    'CHARACTER': 'TEXT',
    'VARCHAR': 'TEXT',
    'VARYING CHARACTER': 'TEXT',
    'NCHAR': 'TEXT',
    'NCHAR VARYING': 'TEXT',
    'NATIVE CHARACTER': 'TEXT',
    'NVARCHAR': 'TEXT',
    'TEXT': 'TEXT',
    'CLOB': 'TEXT',
    'XML': 'TEXT',
    'REAL': 'REAL',
    'DOUBLE': 'REAL',
    'DOUBLE PRECISION': 'REAL',
    'FLOAT': 'REAL',
    'NUMERIC': 'NUMERIC',
    'DECIMAL': 'NUMERIC',
    'BOOLEAN': 'NUMERIC',
    'DATE': 'NUMERIC',
    'DATETIME': 'NUMERIC',
    'BLOB': 'BLOB',
}


def siard_to_sqlite(siard):
    logger = logging.getLogger('essarch.fixity.conversion.backends.siard')
    archive = zipfile.ZipFile(siard, 'r')
    metadata = archive.read('header/metadata.xml')
    parser = etree.XMLParser()
    tree = etree.fromstring(metadata, parser)
    nsmap = {"siard": "http://www.bar.admin.ch/xmlns/siard/2/metadata.xsd"}

    schemas_xpath = tree.xpath('//siard:siardArchive/siard:schemas/siard:schema', namespaces=nsmap)

    for schema in schemas_xpath:
        schema_folder_xpath = schema.xpath('siard:folder', namespaces=nsmap)
        tables_xpath = schema.xpath('siard:tables/siard:table', namespaces=nsmap)
        db = sqlite3.connect(os.path.join(os.path.dirname(siard), f'{schema[0].text}.sqlite'))
        cursor = db.cursor()
        logging.info(f'Creating database {schema[0].text}.sqlite')

        '''CREATE TABLE AND COLUMNS'''
        if len(tables_xpath) != 0:  # Some scehmas lacks tables
            for table in tables_xpath:
                col_dict = {}
                col_lookup = {}
                advanced_type_keys = {}  # sqlite can't handle advanced types, we create fk referenced tables instead
                advanced_fields = {}  # Storage for advanced datatypes (not typed) e.g. VARARRAYS
                lob_keys = {}  # Storage for reference to large binary objects
                col_count = 0
                foreign_keys = set()  # A set to store only unique foreign statements
                columns_xpath = table.xpath('siard:columns/siard:column', namespaces=nsmap)
                folder_xpath = table.xpath('siard:folder', namespaces=nsmap)
                pk_xpath = table.xpath('siard:primaryKey/siard:column', namespaces=nsmap)
                fk_xpath = table.xpath('siard:foreignKeys/siard:foreignKey', namespaces=nsmap)

                for fk in fk_xpath:
                    column_ref = fk.xpath('siard:reference/siard:column', namespaces=nsmap)[0].text
                    referenced_table = fk.xpath('siard:referencedTable', namespaces=nsmap)[0].text
                    referenced_column = fk.xpath('siard:reference/siard:referenced', namespaces=nsmap)[0].text
                    foreign_keys.add(
                        f'FOREIGN KEY("{column_ref}") REFERENCES "{referenced_table}"("{referenced_column}")')

                for column in columns_xpath:
                    datatype_xpath = column.xpath('siard:type', namespaces=nsmap)

                    if (column[1].tag.split("}", 1)[1]) == 'type':
                        fields_xpath = column.xpath('siard:advanced_fields',
                                                    namespaces=nsmap)  # Check for advanced fields

                        if datatype_xpath[0].text.split("(", 1)[0] in mappings:  # Map to sqlite datatypes

                            datatype = mappings[datatype_xpath[0].text.split("(", 1)[0]]
                            col_dict[column[0].text] = datatype
                            col_count += 1
                            col_lookup[col_count] = column[0].text
                            if fields_xpath:
                                advanced_fields[col_count] = column[0].text

                        else:  # Fall back to TEXT if no datatype mapping is found
                            datatype = 'TEXT'
                            col_dict[column[0].text] = datatype
                            col_count += 1
                            col_lookup[col_count] = column[0].text

                            if fields_xpath:
                                advanced_fields[col_count] = column[0].text

                    elif (column[1].tag.split("}", 1)[1]) == 'typeSchema':  # complex objects represented as json
                        col_dict[column[0].text] = 'TEXT'
                        col_count += 1
                        col_lookup[col_count] = column[0].text
                        advanced_type_keys[column[0].text] = column[2].text

                    elif (column[1].tag.split("}", 1)[1]) == 'lobFolder':  # Lob-files are large binary objects
                        col_dict[column[0].text] = 'BLOB'
                        col_count += 1
                        col_lookup[col_count] = column[0].text
                        lob_keys[column[0].text] = column[1].text  # Key = column name, Value = lob folder name

                col_to_create = (', '.join(
                    "'{!s}' {!s}".format(key, val) for (key, val) in col_dict.items()))  # Create column names

                try:
                    if pk_xpath:
                        primary_keys = ('", "'.join([pk.text for pk in pk_xpath]))
                        cursor.execute('CREATE TABLE IF NOT EXISTS "{}" ({},PRIMARY KEY ("{}"){})'
                                       .format(table[0].text,
                                               col_to_create,
                                               primary_keys, ', '.join(foreign_keys) if foreign_keys else '')
                                       )
                    else:
                        cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table[0].text}" ({col_to_create})')

                    db.commit()

                except sqlite3.IntegrityError as e:
                    logger.error(e)

                '''INSERT VALUES INTO TABLE'''
                table_data = archive.read(
                    f'content/{schema_folder_xpath[0].text}/{folder_xpath[0].text}/{folder_xpath[0].text}.xml')

                table_tree = etree.fromstring(table_data, parser)
                nstmap = {"t": table_tree.attrib[table_tree.keys()[0]].split(' ')[0]}

                table_row_xpath = table_tree.xpath('//t:table/t:row', namespaces=nstmap)
                logging.info(f'Inserting values into {table[0].text}')

                for row in table_row_xpath:
                    columns_to_append = []
                    values_to_append = []

                    for i in range(len(row)):

                        col_id = int(row[i].tag.split('}c')[1])  # id for specific column

                        columns_to_append.append(f'"{col_lookup[col_id]}"')

                        if col_lookup[col_id] in advanced_type_keys:
                            json_values = {}

                            for v in row[i].iter():
                                if v.text:
                                    json_values[v.tag.split('}')[1]] = v.text

                            values_to_append.append(json.dumps(str(json_values)))

                        elif col_lookup[col_id] in lob_keys:
                            if row[i].attrib:
                                try:
                                    lob_bin_data = archive.read(row[i].attrib['file'])
                                    values_to_append.append(lob_bin_data)
                                except KeyError:
                                    pass

                            else:
                                values_to_append.append(row[i].text)

                        elif row[i].attrib:
                            lob_bin_data = archive.read(row[i].attrib['file'])
                            values_to_append.append(lob_bin_data)

                        elif col_id in advanced_fields:
                            values_to_append.append(
                                json.dumps(str({elem.text for elem in row[i].iter() if elem.text is not None})))

                        else:
                            values_to_append.append(row[i].text)

                    '''Count number of bindings needed for insert'''
                    bindings = []
                    for binding in range(len(columns_to_append)):
                        bindings.append('?')

                    try:
                        cursor.execute(
                            '''INSERT INTO "{table}" ({column}) VALUES ({values});'''.format(
                                table=table[0].text, column=', '.join(columns_to_append), values=','.join(bindings)),
                            values_to_append)

                    except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                        logger.error(e)

        db.commit()


class SiardConverter(BaseConverter):

    def convert(self, input_file):
        siard_to_sqlite(input_file)

    @staticmethod
    @click.command()
    @click.argument('input_file', metavar='INPUT', type=click.Path(exists=True))
    def cli(input_file):
        """Convert siard to sqlite """
        return SiardConverter().convert(input_file)
