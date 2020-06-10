#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

# from setuptools import setup, find_namespace_packages
# from pkg_resources import parse_requirements

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["requests"]

test_requirements = ["pytest"]

setup(
    author="Jiří Altman",
    author_email="jiri.altman@konicaminolta.cz",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
    ],
    description="Client for the Landscape API (Python 3)",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="landscape_api_py3",
    name="landscape_api_py3",
    packages=find_packages(include=["landscape_api", "landscape_api.*"]),
    # setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/jurya/landscape_api_py3",
    version="0.4.2",
    zip_safe=False,
    entry_points={"console_scripts": ["landscape-api=landscape_api.__main__:cli"]},
    package_data={"landscape_api": ["schemas.json"]},
)
