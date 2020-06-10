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
* Documentation: https://landscape-api-py3.readthedocs.io.

Features
---------

* easy installation from **PyPI** (you can use **pipenv**, **pip**, **pipex**, **Chocolatey**, ...)
* working on **Windows** (**pipx** create **landscape-api.exe** shim)
* working with **Python>=v3.5** (easily **from landscape_api_py3.base import API**)
* for quick use can be installed with **pipx install landscape_api_py3**

Quick start
-----------

Check if you have installed **Python v3.5** and above.

To install Landscape API (Python 3), run this command in your terminal:

On Linux:

.. code-block:: console

    $ pip install landscape-api-py3
    $ python -m landscape-api --uri https://your-uri-to-ls-api/api --key <your API key> --secret <your API secret> --json get-computers --limit 1

On Windows:

.. code-block:: console

    C:\> pip install landscape-api-py3
    C:\> python -m landscape-api --uri https://your-uri-to-ls-api/api --key <your API key> --secret <your API secret> --json get-computers --limit 1

or you can use **pipx** (virtual environment will be created automatically):

On Linux:

.. code-block:: console

    $ pip install --user pipx
    $ pipx ensurepath
    $ exec $SHELL # Restart your shell to reload PATH
    $ pipx install landscape-api-py3
    $ landscape-api --uri https://your-uri-to-ls-api/api --key <your API key> --secret <your API secret> --json get-computers --limit 1

On Windows:

.. code-block:: console

    C:\> pip install --user pipx
    C:\> pipx ensurepath
    C:\> REM Restart console window to reload PATH
    C:\> pipx install landscape-api-py3
    C:\> landscape-api --uri https://your-uri-to-ls-api/api --key <your API key> --secret <your API secret> --json get-computers --limit 1

Known issues
------------

* none (issues with dependencies resolved in v0.3.0)

Credits
-------

Based on package landscape-api_ from `Canonical Ltd.`_
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _landscape-api: https://landscape.canonical.com/static/doc/api/python-api.html
.. _`Canonical Ltd.`: https://canonical.com
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
