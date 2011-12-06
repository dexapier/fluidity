#!/bin/sh
python setup.py sdist
cd dist
tar xfz Fluidity*.tar.gz
cd ..
