# Copyright (c) 2016 EMC Corporation, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from setuptools import setup, find_packages

with open('DESCRIPTION.rst') as description:
    long_description = description.read()
with open("requirements.txt") as requirements:
    install_requires = requirements.readlines()


setup(
    name='emc_midrange_flocker_driver',
    version='0.1',
    description='EMC Midrange Backend Plugin for ClusterHQ/Flocker ',
    long_description=long_description,
    author='Jay Xu',
    author_email='jay.xu@emc.com',
    url='https://github.com/emccode/flocker-drivers/midrange',
    license='Apache 2.0',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='backend, plugin, flocker, docker, python',
    packages=find_packages(),
    install_requires=install_requires,
)
