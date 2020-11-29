import csv
import os
import zipfile

import click
import msoffcrypto


def validate_tv_obj_file(obj, filepath):
    errors = {}
    coruppt_flag = False
    try:
        with obj.tag.information_package.open_file(filepath, "rb") as f:
            if os.path.splitext(filepath)[1] in ['.docx']:
                try:
                    from docx import Document
                    Document(f)
                except KeyError as e:
                    errors[filepath] = 'file is coruppt (%s)' % str(e)
                    coruppt_flag = True
                except zipfile.BadZipFile as e:
                    errors[filepath] = 'file is coruppt (%s)' % str(e)
                    coruppt_flag = True
                except ModuleNotFoundError:
                    pass
            if not coruppt_flag and os.path.splitext(filepath)[1] in ['.docx', '.xlsx']:
                officefile = msoffcrypto.OfficeFile(f)
                if officefile.is_encrypted():
                    errors[filepath] = 'file is encrypted'
    except FileNotFoundError:
        errors[filepath] = 'file not found'

    return errors


def validate_file(filepath, rootdir=None):
    errors = {}
    if rootdir:
        absolute_filepath = os.path.join(rootdir, filepath)
    else:
        absolute_filepath = filepath
    coruppt_flag = False
    try:
        with open(absolute_filepath, "rb") as f:
            if os.path.splitext(absolute_filepath)[1] in ['.docx']:
                try:
                    from docx import Document
                    Document(f)
                except KeyError as e:
                    errors[filepath] = 'file is coruppt (%s)' % str(e)
                    coruppt_flag = True
                except zipfile.BadZipFile as e:
                    errors[filepath] = 'file is coruppt (%s)' % str(e)
                    coruppt_flag = True
                except ModuleNotFoundError:
                    pass
            if not coruppt_flag and os.path.splitext(filepath)[1] in ['.docx', '.xlsx']:
                officefile = msoffcrypto.OfficeFile(f)
                if officefile.is_encrypted():
                    errors[filepath] = 'file is encrypted'
    except FileNotFoundError:
        errors[filepath] = 'file not found'

    return errors


def validate_dir(path, rootdir=None):
    errors = {}
    if rootdir:
        absolute_path = os.path.join(rootdir, path)
    else:
        absolute_path = path
    if os.path.exists(absolute_path):
        for root, _dirs, files in os.walk(absolute_path):
            for f in files:
                filepath = os.path.join(root, f)
                if rootdir:
                    rel_filepath = os.path.relpath(filepath, rootdir)
                    errors.update(validate_file(rel_filepath, rootdir))
                else:
                    errors.update(validate_file(filepath))
    else:
        errors[path] = 'path not found'

    return errors


def generate_error_report(errors, reportfile, rootdir=None):
    if rootdir:
        reportfile = os.path.join(rootdir, reportfile)
    with open(reportfile, 'w', newline='', encoding="utf8") as csvfile:
        fieldnames = ['filepath', 'note']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        for k, v in errors.items():
            writer.writerow({'filepath': k, 'note': v})


@click.command()
@click.option('--path', default='content', help='Path inside IP, example content')
@click.option('--rootdir', default='', help='Absolute path to IP, example c:/testdata')
@click.option('--reportfile', default='metadata/file_report.csv', help='Path inside IP to reportfile, example metadata/file_report.csv')
def cli(path, rootdir, reportfile):
    # print('path: %s, rootdir: %s, reportfile: %s' % (path, rootdir, reportfile))
    generate_error_report(validate_dir(path, rootdir), reportfile, rootdir)


if __name__ == '__main__':
    cli()
