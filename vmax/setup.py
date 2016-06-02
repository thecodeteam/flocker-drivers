# Copyright Hybrid Logic Ltd.
# Copyright 2015 EMC Corporation
# See LICENSE file for details.

from setuptools import setup, find_packages
import codecs  # To use a consistent encoding

# Get the long description from the relevant file
with codecs.open('DESCRIPTION.rst', encoding='utf-8') as f:
    long_description = f.read()

with open("requirements.txt") as requirements:
    install_requires = requirements.readlines()

setup(
    name='emc_vmax_flocker_plugin',
    version='0.9.2',
    description='EMC VMAX Backend Plugin for ClusterHQ/Flocker ',
    long_description=long_description,
    author='Kevin Rodgers',
    author_email='kevin.rodgers@emc.com',
    url='https://github.com/emccode/flocker-drivers/vmax',
    license='Apache 2.0',

    classifiers=[

    'Development Status :: 4 - Beta',

    'Intended Audience :: System Administrators',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',

    'License :: OSI Approved :: Apache Software License',

    # Python versions supported
    'Programming Language :: Python :: 2.7',
    ],

    keywords='backend, plugin, flocker, docker, python',
    packages=find_packages(exclude=['test*']),
    install_requires=install_requires,
    data_files=[]
)
