#!/usr/bin/env bash

. $NOVA_CI_HOME/test_util.sh

$LTP=$(clone_or_pull git@github.com:NVSL/NOVA-ltp.git)

(cd $LTP
 make autotools
 ./configure
 make
 sudo make install
 sudo /opt/ltp/runltp -f nova -d $NOVA_CI_PRIMARY_FS $* | tee ${NOVA_CI_LOG_DIR}/nova-ltp-results.out
 ./to_junit.py < ${NOVA_CI_LOG_DIR}/nova-ltp-results.out > ${NOVA_CI_LOG_DIR}/nova-ltp-results.xml
)

