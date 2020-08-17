# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

PYTHON_LIB_PATH = os.path.abspath('../..')
sys.path.insert(0, PYTHON_LIB_PATH)

# -- Project information -----------------------------------------------------

project = 'Prologin System Administration'
copyright = '(C) 2013-2020 Association Prologin'
author = 'Association Prologin'

# The full version, including alpha/beta/rc tags
release = '2020'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx_rtd_theme',
    'sphinxcontrib.apidoc',
]

# Don't hide todo items
todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Options for LaTeX output

latex_engine = 'xelatex'


# -- apidoc & autodoc options

apidoc_module_dir = os.path.join(PYTHON_LIB_PATH, 'prologin')
apidoc_output_dir = 'api'
apidoc_excluded_paths = [
    '*/migrations/*',
    '*/*/migrations/*',
]
apidoc_separate_modules = True

# These modules can't be imported without requiring special config.
autodoc_mock_imports = [
    'django',
    'django_prometheus',
    'prologin.concours.settings',
    'prologin.config',
    'prologin.mdb.settings',
    'prologin.udb.settings',
    'prologin.utils.django',
    'prologin.wiki.settings',
    'prologin.concours.stechec.models',
    'prologin.concours.stechec.urls',
    'prologin.concours.restapi.models',
    'prologin.concours.restapi.urls',
    'prologin.homepage.models',
    'prologin.homepage.views',
    'prologin.homepage.urls',
    'rest_framework',
]
