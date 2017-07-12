#!/usr/bin/env bash

. $NOVA_CI_HOME/test_util.sh

LTP=$(clone_or_pull git@github.com:NVSL/NOVA-ltp.git)

cd $LTP

if [ ".yes" == ".$REBUILD" ]; then
    make autotools
    ./configure
    make
    sudo make install
else
    # I don't know why this is necessary, but the runltp binary disappears...
    sudo cp ./runltp /opt/ltp/runltp
    sudo cp ./runtest/* /opt/ltp/runtest/
fi
sudo /opt/ltp/runltp -f nova-empty -d $NOVA_CI_PRIMARY_FS $* 2>&1 | tee ${NOVA_CI_LOG_DIR}/nova-ltp-results.out
#./to_junit.py < ${NOVA_CI_LOG_DIR}/nova-ltp-results.out > ${NOVA_CI_LOG_DIR}/nova-ltp-results.xml


