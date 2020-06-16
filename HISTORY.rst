=======
History
=======

v0.6.0 (2020-06-17)
-------------------
- fix #19
- minor updates

v0.5.0 (2020-06-11)
-------------------
* added support for Python 3.5, 3.6, 3.7, 3.8 and above
* fixed minor bugs
* updated documentation (Installation, Usage, Quick start)

v0.4.2 (2020-06-10)
-------------------
* fixed documentation import bug
* fixed default CA cert bug

v0.4.1 (2020-06-10)
-------------------
* fixed bug with imports - now it's compatible with Canonical **landscape-api**

v0.3.5 (2020-06-10)
-------------------
* minor fixes

v0.3.4 (2020-06-09)
-------------------
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
