=======
History
=======

v0.3.0 (2020-06-09) - First pre-release of landscape-api package
----------------------------------------------------------------------
* replaced **pycurl** --> **requests**

v0.2.0alpha (2020-06-08) - First pre-release of landscape-api package
----------------------------------------------------------------------
* 🎉 first **ALPHA non-production** version release of **landscape-api** ported to **Python v3.8**

Known issues (v0.2.0alpha):
~~~~~~~~~~~~~~~~~~~~~~~~~~~
* on **Windows** download CA certificate file from `<https://curl.haxx.se/ca/cacert.pem>`_ and use **--ssl-ca-file** or **LANDSCAPE_API_SSL_CA_FILE** (see Landscape API documentation `here <https://landscape.canonical.com/static/doc/api/api-client-package.html>`_)
* on **Linux** depends on **gnutls** and **libssl** (require **pycurl** package for installation)

Before installation of the package (v0.2.0alpha):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* on **Ubuntu 16.04** (Xenial Xerus) use **sudo apt-get install -y libgnutls-dev**
* on **Ubuntu 20.04** (Focal Fossa) use **sudo apt-get install -y libgnutls28-dev libcurl4-openssl-dev libssl-dev**
* on **Windows 10** simply use **pipx install landscape_api_py3**

0.1.3 (2020-06-07)
------------------
* first release on PyPI
