#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='hitsl_utils',
    version='0.2.2',
    url='https://stash.bars-open.ru/scm/medvtr/hitsl.utils.git',
    author='hitsl',
    description='Small utilities used in HITSL',
    long_description=read('README.md'),
    include_package_data=True,
    packages=['hitsl_utils'],
    platforms='any',
    install_requires=[
        'Flask',
        'pytz',
        'Requests',
        'Blinker',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
