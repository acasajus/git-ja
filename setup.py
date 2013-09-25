#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup
import gitja

setup(
    name = 'git-ja',
    version = gitja.VERSION,
    author = 'Adria Casajus',
    author_email = 'adriancasajus@gmail.com',
    packages = [ 'gitja' ],
    scripts = [ 'bin/git-ja' ],
    url = 'https://github.com/acasajus/git-ja',
    license = 'LICENSE',
    description = 'Git utilities for gitjas',
    long_description = open('README.rst').read(),
    )