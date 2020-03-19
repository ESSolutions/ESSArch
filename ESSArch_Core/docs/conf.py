"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

# -*- coding: utf-8 -*-
#
# ESSArch documentation build configuration file, created by
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

import os
import sys
from datetime import datetime

from ESSArch_Core._version import get_versions

proj_folder = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '../..'))

sys.path.append(proj_folder)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ESSArch_Core.config.settings')
import django  # noqa isort:skip
django.setup()

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autosectionlabel', 'sphinx.ext.inheritance_diagram',
              'sphinx.ext.intersphinx', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode', 'sphinxcontrib.httpdomain',
              'sphinxcontrib.httpexample', 'sphinxcontrib.inlinesyntaxhighlight']

# True to prefix each section label with the name of the document it is in,
# followed by a colon. For example, index:Introduction for a section called
# Introduction that appears in document index.rst. Useful for avoiding
# ambiguity when the same section heading appears in different documents.
autosectionlabel_prefix_document = True

suppress_warnings = [
    'autosectionlabel.*',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.7', None),
    'sphinx': ('http://www.sphinx-doc.org/en/master/', None),
    'django': ('https://docs.djangoproject.com/en/dev/', 'https://docs.djangoproject.com/en/dev/_objects/'),
    'celery': ('https://celery.readthedocs.io/en/latest/', None),
}

# Github link
html_context = {
    'display_github': True,
    'github_user': 'essolutions',
    'github_repo': 'essarch',
    'github_version': 'master/ESSArch_Core/docs/'
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
project = 'ESSArch'
copyright = '{}, ES Solutions'.format(datetime.now().year)
author = 'ES Solutions'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = get_versions()['version']
# The full version, including alpha/beta/rc tags.
release = get_versions()['full-revisionid']

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
pygments_style = 'default'

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
html_theme_options = {
    'collapse_navigation': False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'ESSArchdoc'


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
    (master_doc, 'ESSArch.tex', 'ESSArch Documentation',
     'ES Solutions', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'essarchcore', 'ESSArch Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'ESSArch', 'ESSArch Documentation',
     author, 'ESSArch', 'One line description of project.',
     'Miscellaneous'),
]
