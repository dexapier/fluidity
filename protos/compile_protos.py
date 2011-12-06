#!/usr/bin/python

import os
import shutil
import subprocess
import sys


subprocess.call("protoc --python_out=. *.proto", shell=True)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dest_path = os.path.join(parent_dir, 'fluidity/models.py')
print "Moving generated model proto file to: " + dest_path
shutil.move('models_pb2.py', dest_path)

