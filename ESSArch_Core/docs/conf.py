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

# -*- coding: utf-8 -*-
#
# ESSArch Core documentation build configuration file, created by
# sphinx-quickstart on Wed Jan 25 14:11:42 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

import importlib
import inspect
import os
import sys

proj_folder = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '../..'))

sys.path.append(proj_folder)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Stop Django from executing DB queries
from django.db.models.query import QuerySet
QuerySet.__repr__ = lambda self: self.__class__.__name__

try:
    import enchant  # NoQA
except ImportError:
    enchant = None


def skip_queryset(app, what, name, obj, skip, options):
    """Skip queryset subclasses to avoid database queries."""
    from django.db import models
    if isinstance(obj, (models.QuerySet, models.manager.BaseManager)) or name.endswith('objects'):
        return True
    return skip


def process_django_models(app, what, name, obj, options, lines):
    """Append params from fields to model documentation."""
    from django.utils.encoding import force_text
    from django.utils.html import strip_tags
    from django.db import models

    spelling_white_list = ['', '.. spelling::']

    if inspect.isclass(obj) and issubclass(obj, models.Model):
        for field in obj._meta.fields:
            help_text = strip_tags(force_text(field.help_text))
            verbose_name = force_text(field.verbose_name).capitalize()

            if help_text:
                lines.append(':param %s: %s - %s' % (field.attname, verbose_name,  help_text))
            else:
                lines.append(':param %s: %s' % (field.attname, verbose_name))

            if enchant is not None:
                from enchant.tokenize import basic_tokenize

                words = verbose_name.replace('-', '.').replace('_', '.').split('.')
                words = [s for s in words if s != '']
                for word in words:
                    spelling_white_list += ["    %s" % ''.join(i for i in word if not i.isdigit())]
                    spelling_white_list += ["    %s" % w[0] for w in basic_tokenize(word)]

            field_type = type(field)
            module = field_type.__module__
            if 'django.db.models' in module:
                # scope with django.db.models * imports
                module = 'django.db.models'
            lines.append(':type %s: %s.%s' % (field.attname, module, field_type.__name__))
        if enchant is not None:
            lines += spelling_white_list
    return lines


def process_modules(app, what, name, obj, options, lines):
    """Add module names to spelling white list."""
    if what != 'module':
        return lines
    from enchant.tokenize import basic_tokenize

    spelling_white_list = ['', '.. spelling::']
    words = name.replace('-', '.').replace('_', '.').split('.')
    words = [s for s in words if s != '']
    for word in words:
        spelling_white_list += ["    %s" % ''.join(i for i in word if not i.isdigit())]
        spelling_white_list += ["    %s" % w[0] for w in basic_tokenize(word)]
    lines += spelling_white_list
    return lines

def setup(app):
    # Register the docstring processor with sphinx
    app.connect('autodoc-process-docstring', process_django_models)
    app.connect('autodoc-skip-member', skip_queryset)
    if enchant is not None:
        app.connect('autodoc-process-docstring', process_modules)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinxtogithub', 'sphinx.ext.autodoc', 'sphinx.ext.autosectionlabel', 'sphinx.ext.inheritance_diagram', 'sphinx.ext.intersphinx', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode', 'sphinxcontrib.httpdomain']

# True to prefix each section label with the name of the document it is in,
# followed by a colon. For example, index:Introduction for a section called
# Introduction that appears in document index.rst. Useful for avoiding
# ambiguity when the same section heading appears in different documents.
autosectionlabel_prefix_document = True

intersphinx_mapping = {
    'python': ('https://docs.python.org/2.7', None),
    'celery': ('https://celery.readthedocs.org/en/latest/', None),
    'django': ('https://docs.djangoproject.com/en/1.11/', 'https://docs.djangoproject.com/en/1.11/_objects/'),
    'sphinx': ('http://sphinx.pocoo.org/', None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ESSArch Core'
copyright = u'2017, ES Solutions'
author = u'ES Solutions'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = u'1.0.0'
# The full version, including alpha/beta/rc tags.
release = u'1.0.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

gettext_compact = False
locale_dirs = ['locale']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'ESSArchCoredoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'ESSArchCore.tex', u'ESSArch Core Documentation',
     u'ES Solutions', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'essarchcore', u'ESSArch Core Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'ESSArchCore', u'ESSArch Core Documentation',
     author, 'ESSArchCore', 'One line description of project.',
     'Miscellaneous'),
]
