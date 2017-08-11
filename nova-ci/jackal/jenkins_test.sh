#!/usr/bin/bash


./prepare_env.sh
. venv/bin/activate

set -v

./run_tests.py --runner gce -v --tests xfstests1 --configs baseline --dont_kill_runner --instance_prefix jenkins-test --reuse_image
