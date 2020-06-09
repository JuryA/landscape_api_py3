.. highlight:: shell
<<<<<<< HEAD

=======
>>>>>>> 62d3a5839f5a73d9bb29838dfda6e61c7f863a90
========================
Landscape API (Python 3)
========================


.. image:: https://img.shields.io/pypi/v/landscape_api_py3.svg
        :target: https://pypi.python.org/pypi/landscape_api_py3

.. image:: https://img.shields.io/travis/jurya/landscape_api_py3.svg
        :target: https://travis-ci.org/jurya/landscape_api_py3

.. image:: https://readthedocs.org/projects/landscape-api-py3/badge/?version=latest
        :target: https://landscape-api-py3.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Client for the Landscape API (Python 3)

* Free software: MIT license

.. * Documentation: https://landscape-api-py3.readthedocs.io.

Features
---------
* easy installation from **PyPI** (you can use **pipenv**, **pip**, **pipex**, **Chocolatey**, ...)
* working on **Windows** (**piped** create **landscape-api.exe** shim)
* working with **Python>=v3.8** (easily **import landscape_api_py3**)
* for quick use can be installed with **pipx install landscape_api_py3**

Known issues
-------------
* none (issues with dependencies resolved in v0.3.0)

Installation of the package
----------------------------
::
    $ pipx install landscape_api_py3

Usage
------
::
    $ landscape-api [OPTIONS] ACTION [ACTION OPTIONS] [ARGS]

For help::
    $ landscape-api --help

Before use it's recommended to configure these ENV VARS: LANDSCAPE_API_KEY, LANDSCAPE_API_SECRET, LANDSCAPE_API_URI

Credits
-------

Based on package landscape-api_ from `Canonical Ltd.`_
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _landscape-api: https://landscape.canonical.com/static/doc/api/python-api.html
.. _`Canonical Ltd.`: https://canonical.com
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
