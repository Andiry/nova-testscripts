#!/usr/bin/env bash 

if ! [ -f test_funcs.sh ]; then
    echo You are running in the wrong directory.
    exit 1
fi

. ./test_funcs.sh
init_tests
do_run_tests $*
