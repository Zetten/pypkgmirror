#!/usr/bin/env python
#
# Copyright 2015 Peter van Zetten
#
# This file is part of pypkgmirror.
#
# pypkgmirror is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pypkgmirror is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pypkgmirror.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

setup(
    name='pypkgmirror',
    version='0.1.0',
    url='',
    license='',
    author='Zetten',
    author_email='',
    description='',
    requires=['pyyaml'],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pypkgmirror = pypkgmirror:main',
        ]
    }
)
