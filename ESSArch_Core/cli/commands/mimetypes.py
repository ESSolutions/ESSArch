import os
import shutil

import click

from ESSArch_Core import BASE_DIR
from ESSArch_Core.cli import deactivate_prompts

DEFAULT_TEMPLATE = os.path.join(BASE_DIR, 'config/mime.types.default')


@click.command()
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('-t', '--template', default=DEFAULT_TEMPLATE)
@click.option('--overwrite/--no-overwrite', default=None)
@click.option('-p', '--path', type=str, prompt=True, default='/ESSArch/config/mime.types',
              show_default='/ESSArch/config/mime.types')
def generate(path, overwrite, template):
    """Generate mime.types file
    """
    if os.path.isfile(path) and overwrite is None:
        overwrite = click.confirm("File at '%s' already exists, should we overwrite it?" % click.format_filename(path))

    if not os.path.isfile(path) or overwrite:
        shutil.copyfile(template, path)
