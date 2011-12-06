#!/bin/sh
protoc --python_out=. *.proto  # --java_out=.
mv models_pb2.py ../fluidity/models.py

