#!/usr/bin/env bash

. $NOVA_CI_HOME/test_util.sh

export FSTEST=$(clone_or_pull https://github.com/NVSL/pjd-fstest.git)

set -v

cd $FSTEST

make

pwd
P=$PWD
cd $NOVA_CI_PRIMARY_FS
sudo prove -r $* $P | tee ${NOVA_CI_LOG_DIR}/fstest-results.out
#sudo ./to_junit.py < ${NOVA_CI_LOG_DIR}/xfstests-results.out > ${NOVA_CI_LOG_DIR}/xfstests-results.xml



