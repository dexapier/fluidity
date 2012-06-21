#!/usr/bin/python

import os
import shutil
import subprocess


BASE_HEADER = "# Generated by the protocol buffer compiler.  DO NOT EDIT!"
PYLINT_IGNORE = "\n\n#pylint: disable-msg=F0401,W0311,R0903,W0232,W0611,W0301"  # IGNORE:E0012
PYDEV_IGNORE = "\n#@PydevCodeAnalysisIgnore"
NEW_HEADER = BASE_HEADER + PYLINT_IGNORE + PYDEV_IGNORE
OUTPUT_FILE = 'models_protos_pb2.py'


def fix_protobuf_warnings():
    with open(OUTPUT_FILE, 'r') as models:
        models_text = models.read()
    with open(OUTPUT_FILE, 'w') as models:
        models.write(models_text.replace(BASE_HEADER, NEW_HEADER))

def main():
    subprocess.call("protoc --python_out=. --java_out=. *.proto", shell=True)
    print "Killing stupid PyLint warnings in the generated protobuf code..."
    fix_protobuf_warnings()

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_path = os.path.join(parent_dir, 'fluidity/models_protos.py')
    print "Moving generated model proto file to: " + dest_path
    shutil.move(OUTPUT_FILE, dest_path)


if __name__ == "__main__":
    main()

