#!/usr/bin/env bash 

if ! [ -f test_funcs.sh ]; then
    echo You are running in the wrong directory.
    exit 1
fi

. ./test_funcs.sh

(
    set -v
    init_tests
    get_packages
    update_and_build_nova
    mount_nova
    run_tests $*
) 2>&1 | tee  $NOVA_CI_LOG_DIR/run_test.log
