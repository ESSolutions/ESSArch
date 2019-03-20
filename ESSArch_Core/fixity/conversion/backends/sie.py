import click
import csv
import logging
import shlex
from datetime import datetime

from ESSArch_Core.fixity.conversion.backends.base import BaseConverter

logger = logging.getLogger('essarch.fixity.conversion.backends.sie')

ACCOUNT_GROUP = {
    '1': '1 - Tillgångar',
    '2': '2 - Eget kapital och skulder',
    '3': '3 - Rörelsens inkomster och intäkter',
    '4': '4 - Utgifter och kostnader förädling',
    '5': '5 - Övriga externa rörelseutgifter och kostnader',
    '6': '6 - Övriga externa rörelseutgifter och kostnader',
    '7': '7 - Utgifter och kostnader för personal, avskrivningar mm.',
    '8': '8 - Finansiella och andra inkomster/intäkter och utgifter/kostnader'
}


def sie_parser(src, dst, encoding=None):
    with open(dst, 'w') as output_file:
        header = [
            "Date",
            "DateMonth",
            "Account",
            "Account group",
            "Account name",
            "Kst",
            "Proj",
            "Amount",
            "Text",
            "Verification",
            "DateKey",
            "Company"
        ]

        writer = csv.writer(output_file, quoting=csv.QUOTE_ALL, lineterminator='\n')
        writer.writerow(header)

        with open(src, 'r', encoding=encoding) as inputfile:
            writer.writerows(create_csv_row(inputfile.readlines()))


def create_csv_row(content):
    attribute_fnamn = "Okänd"
    attribute_accounts = {}
    attribute_dims = {}
    attribute_kst = {}
    attribute_proj = {}
    verifications = []

    for line_number, line in enumerate(content):
        if not line.startswith('#') or len(line.split(' ')) == 0:
            continue

        label, parts = parse(line)

        if label == "FNAMN":
            attribute_fnamn = parts[0]

        elif label == "KONTO":
            attribute_accounts[parts[0]] = parts[1]

        elif label == "DIM":
            attribute_dims[parts[0]] = parts[1]

        elif label == "OBJEKT":
            if parts[0] == '1':
                attribute_kst[parts[1]] = parts[2]

            elif parts[0] == '6':
                attribute_proj[parts[1]] = parts[2]

        elif label == "VER":
            verno = parts[1]
            verdate = parts[2]
            if len(parts) > 3:
                vertext = parts[3]
            else:
                vertext = ""
            vers = parse_ver(content, line_number, vertext, verdate, verno)
            verifications.extend(vers)

    for ver in verifications:
        account_name = ""
        proj_name = ver["proj_nr"]
        kst_name = ver["kst"]

        if ver["account"] in attribute_accounts:
            account_name = attribute_accounts[ver["account"]]

        if ver["kst"] in attribute_kst:
            kst_name = attribute_kst[ver["kst"]]

        if ver["proj_nr"] in attribute_proj:
            proj_name = attribute_proj[ver["proj_nr"]]

        verdate = datetime.strptime(ver["verdate"], "%Y%m%d")
        row = [
            verdate.strftime('%Y-%m-%d'),
            verdate.strftime('%Y-%m'),
            ver["account"],
            ACCOUNT_GROUP[ver["account"][0]],
            account_name,
            kst_name,
            proj_name,
            "%0.0f" % float(ver["amount"]),
            ver["vertext"],
            ver["verno"],
            verdate.strftime("%s"),
            attribute_fnamn,
        ]

        yield row


def parse(line):
    if not line.startswith('#') or len(line.split(' ')) == 0:
        return False, False

    parts = shlex.split(line.replace('{', '"').replace('}', '"'))
    label = parts[0].upper()[1:]
    return label, parts[1:]


def parse_ver(content, line, default_vertext, default_verdate, verno):
    vers = []

    if content[line + 1].startswith('{'):
        line = line + 2
        while not content[line].startswith('}'):
            label, parts = parse(content[line].strip())
            kst = ""
            proj = ""
            account = parts[0]
            p = parts[1]
            amount = parts[2]

            if len(parts) > 3:
                verdate = parts[3]
            else:
                verdate = default_verdate

            if len(parts) > 4:
                vertext = parts[4]
            else:
                vertext = default_vertext

            if len(p.split(' ')) > 0 and p.split(' ')[0] == '1':
                kst = p.split(' ')[1]

            if len(p.split(' ')) > 2 and p.split(' ')[2] == '6':
                proj = p.split(' ')[3]

            vers.append({
                'account': account,
                'kst': kst,
                'proj_nr': proj,
                'amount': amount,
                'verdate': verdate,
                'vertext': vertext,
                'verno': verno
            })
            line = line + 1

    return vers


class SIEConverter(BaseConverter):
    input_formats = [
        'text/sie',
    ]

    output_formats = [
        'text/csv',
    ]

    def convert(self, input_file, output_file, in_fmt=None, out_fmt=None, encoding=None, **kwargs):
        sie_parser(input_file, output_file, encoding=encoding)

    @staticmethod
    @click.command()
    @click.argument('input_file', metavar='INPUT', type=click.Path(exists=True))
    @click.argument('output_file', metavar='OUTPUT', type=click.Path())
    @click.option('--in-fmt', 'in_fmt', type=click.Choice(input_formats), help="Format of the input file")
    @click.option('--out-fmt', 'out_fmt', type=click.Choice(output_formats), help="Format of the output file")
    def cli(input_file, output_file, in_fmt, out_fmt):
        """Convert SIE files"""
        return SIEConverter().convert(input_file, output_file, in_fmt, out_fmt)
