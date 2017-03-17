# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from pip.req import parse_requirements
import re, ast

# get version from __version__ variable in aptitudetech_private/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('aptitudetech_private/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

requirements = parse_requirements("requirements.txt", session="")

setup(
	name='aptitudetech_private',
	version=version,
	description='Private app',
	author='Aptitudetech',
	author_email='support@aptitudetech.net',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[str(ir.req) for ir in requirements],
	dependency_links=[str(ir._link) for ir in requirements if ir._link]
)
