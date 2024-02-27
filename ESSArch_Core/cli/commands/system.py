import click

from ESSArch_Core._version import get_versions


@click.command()
def version():
    """Show ESSArch version
    """
    versions_dict = get_versions()
    print("Version: {} - {}".format(versions_dict['version'], versions_dict['full-revisionid']))
