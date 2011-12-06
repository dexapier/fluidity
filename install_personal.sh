#!/bin/sh
python make_clean.py
sh build.sh
cd dist/Fluidity*
sh ./install.sh
cd ../..
chown jensck: /home/jensck/workspace/Fluidity -R
/bin/rm dist -fr
find . -name '*.pyc' -delete

