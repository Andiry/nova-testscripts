#!/usr/bin/bash

./prepare_env.sh
. venv/bin/activate
#./run_tests.py --runner gce -v --tests xfstests1 --configs baseline --instance_prefix test --configs all --tests xfstests-all
./run_tests.py --runner gce  --tests xfstests1 --configs baseline --instance_prefix jenkins --configs baseline-0-0-0-1-0-0 baseline-0-0-0-0-0-0 baseline-1-1-1-0-1-1 --tests xfstests-all
