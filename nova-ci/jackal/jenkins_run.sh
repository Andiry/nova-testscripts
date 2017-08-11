#!/usr/bin/bash

./prepare_env.sh
. venv/bin/activate

case "$1" in
    core)
	args="--configs baseline --instance_prefix jenkins --configs baseline-0-0-0-1-0-0 baseline-0-0-0-0-0-0 baseline-1-1-1-0-1-1 --tests xfstests-all";;
    test)
	args="-v --tests xfstests1 --configs baseline --dont_kill_runner --instance_prefix jenkins-test --reuse_image";;
esac

echo ./run_tests.py --runner gce  --dont_double_expect  $args
