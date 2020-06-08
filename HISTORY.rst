=======
History
=======

v0.2.0alpha (2020-06-08) - First pre-release of landscape-api package
----------------------------------------------------------------------
## 🎉 First **ALPHA non-production** version release of `landscape-api` ported to **Python v3.8**

Features:
~~~~~~~~~
* Easy installation from **PyPI** (you can use `pipenv`, `pip`, `pipex`, `Chocolatey`, ...)
* Working on **Windows** (`piped` create `landscape-api.exe` shim)
* Working with `Python>=v3.8` (easily `import landscape_api_py3`)
* For quick use can be installed with `pipx install landscape_api_py3`

Known issues:
~~~~~~~~~~~~~
* On **Windows** download CA certificate file from `<https://curl.haxx.se/ca/cacert.pem>`_ and use `--ssl-ca-file` or **LANDSCAPE_API_SSL_CA_FILE** (see Landscape API documentation `here <https://landscape.canonical.com/static/doc/api/api-client-package.html>`_)
* On **Linux** depends on `gnutls` and `libssl` (require `pycurl` package for installation)

Before installation of the package:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* On **Ubuntu 16.04** (Xenial Xerus) use `sudo apt-get install -y libgnutls-dev`
* On **Ubuntu 20.04** (Focal Fossa) use `sudo apt-get install -y libgnutls28-dev libcurl4-openssl-dev libssl-dev`
* On Windows 10 simply use `pipx install landscape_api_py3`

**Usage:**

`landscape-api [OPTIONS] ACTION [ACTION OPTIONS] [ARGS]`

For help: `landscape-api --help`
Before use it's recommended to configure these ENV VARS:
* **LANDSCAPE_API_KEY**
* **LANDSCAPE_API_SECRET**
* **LANDSCAPE_API_URI**

0.1.3 (2020-06-07)
------------------

* First release on PyPI.
