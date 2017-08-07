#!/usr/bin/bash

./prepare_env.sh
. venv/bin/activate
run_tests.py --runner gce --instance_prefix jenkins
