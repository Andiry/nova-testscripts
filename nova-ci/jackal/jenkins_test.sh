#!/usr/bin/bash

./build_venv.sh
. venv/bin/activate
./run_tests.py --runner gce -v --tests xfstests1 --configs baseline1
