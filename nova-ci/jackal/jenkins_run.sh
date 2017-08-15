#!/usr/bin/bash

./prepare_env.sh
. venv/bin/activate

mode=$1
case "$mode" in
    core)
	args="--configs baseline --instance_prefix jenkins --configs baseline-0-0-0-1-0-0 baseline-0-0-0-0-0-0 baseline-1-1-1-0-1-1 --tests xfstests-all --dont_kill_runner --reuse_image"
	shift;;
    test)
	args="-v --tests xfstests1 xfstests2 --configs baseline baseline2 --dont_kill_runner --instance_prefix jenkins-test --reuse_image"
	shift;;
    sweep)
	args="--instance_prefix jenkins --reuse_image"
	shift;;
esac

./run_tests.py --runner gce  --dont_double_expect  $args $*
