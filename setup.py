#!/usr/bin/env python3

# Copyright 2018 Comcast Cable Communications Management, LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
The setuptools-based install script for connvitals-monitor
"""

import os

# RPMs generated for fedora/rhel/centos need to have a different name
# (debian/ubuntu automatically prepends python3-, but those do not)
import platform
from setuptools import setup, find_packages

pkgname = "connmonitor"
depname = "connvitals"

# I know this is deprecated, but it's the only way to get this information afaik
distname = platform.linux_distribution(full_distribution_name=False)[0]
if distname in  {'centos', 'fedora', 'redhat'}:
	pkgname = "python3-"+pkgname
	depname = "python3-"+depname
elif not distname:
	from sys import stderr
	print("\033[38;2;255;0;0mconnvitals-monitor ONLY works on compatible *nix \
distributions - '%s' is not supported.\033[38;2;255;255;255m" % platform.system(), file=stderr)
	exit(1)

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
	long_description = f.read()

setup(
	name=pkgname,
	version='3.0.3',
	description=\
	'Uses the connvitals library to continuously poll and record network connectivity statistics.',
	long_description=long_description,
	url='https://github.com/comcast/connvitals-monitor',
	author='Brennan Fieck',
	author_email='Brennan_WilliamFieck@comcast.com',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Intended Audience :: Telecommunications Industry',
		'Intended Audience :: Developers',
		'Intended Audience :: Information Technology',
		'Topic :: Internet',
		'Topic :: Internet :: Log Analysis',
		'Topic :: Internet :: WWW/HTTP',
		'Topic :: Scientific/Engineering :: Information Analysis',
		'Topic :: System :: Logging',
		'Topic :: System :: Monitoring',
		'Topic :: System :: Networking :: Monitoring',
		'Topic :: System :: Networking :: Monitoring :: Hardware Watchdog',
		'Topic :: Utilities',
		'License :: OSI Approved :: Apache Software License',
		'Environment :: No Input/Output (Daemon)',
		'Environment :: Console',
		'Operating System :: POSIX :: Linux',
		'Programming Language :: Python :: Implementation :: CPython',
		'Programming Language :: Python :: Implementation :: PyPy',
		'Programming Language :: Python :: 3 :: Only',
		'Programming Language :: Python :: 3.4',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7'
	],
	keywords='network statistics connection ping traceroute port ip',
	packages=find_packages(exclude=['contrib', 'docs', 'tests']),
	install_requires=[depname, 'setuptools', 'typing'],
	data_files=[('/usr/lib/systemd/system', ['connmonitor.service'])],
	entry_points={
		'console_scripts': [
			'connmonitor=connmonitor:main',
		],
	},
	python_requires='~=3.4'
)
