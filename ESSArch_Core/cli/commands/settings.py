import os

import click

from ESSArch_Core import BASE_DIR
from ESSArch_Core.cli import deactivate_prompts
from ESSArch_Core.config import generate_local_settings

DEFAULT_TEMPLATE = os.path.join(BASE_DIR, 'config/local_settings.default')


def create_local_settings_file(path, template, overwrite=None, debug=False):
    content = generate_local_settings(template, debug=debug)

    if os.path.isfile(path) and overwrite is None:
        overwrite = click.confirm("File at '%s' already exists, should we overwrite it?" % click.format_filename(path))

    if not os.path.isfile(path) or overwrite:
        with click.open_file(path, 'w') as fp:
            fp.write(content)


@click.command()
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('--debug', is_flag=True, prompt=True, default=False)
@click.option('-t', '--template', default=DEFAULT_TEMPLATE)
@click.option('--overwrite/--no-overwrite', default=None)
@click.option('-p', '--path', type=str, prompt=True, default='/ESSArch/config/local_essarch_settings.py',
              show_default='/ESSArch/config/local_essarch_settings.py')
def generate(path, overwrite, template, debug):
    """Generate settings file
    """

    create_local_settings_file(path, template=template, overwrite=overwrite, debug=debug)
