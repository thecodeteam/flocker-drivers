# Copyright 2015 EMC Corporation

from setuptools import setup, find_packages
import codecs  # To use a consistent encoding
from os import path

# Get the long description from the relevant file
with codecs.open('DESCRIPTION.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='emc_xtremio_flocker_driver',
    version='1.0',
    description='EMC XtremIO Backend Plugin for ClusterHQ/Flocker ',
    long_description=long_description,
    author='Vaibhav Khanduja',
    author_email='vaibhavkhanduja@yahoo.com',
    url='https://github.com/emccorp/xtremio-flocker-driver',
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
    data_files=[('/etc/flocker/', ['example_xio_agent.yml'])]
)
