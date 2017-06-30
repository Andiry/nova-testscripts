#!/usr/bin/env bash

. $NOVA_CI_HOME/test_util.sh

$XFSTESTS=$(clone_or_pull git@github.com:NVSL/xfstests.git)

export FSTYP=NOVA
export TEST_DEV=/dev/pmem0
export TEST_DIR=/mnt/ramdisk
export SCRATCH_DEV=/dev/pmem1
export SCRATCH_MNT=/mnt/scratch

(cd $XFSTEST
 sudo apt-get install xfslibs-dev uuid-dev libtool-bin \
      e2fsprogs automake gcc libuuid1 quota attr libattr1-dev make \
      libacl1-dev libaio-dev xfsprogs libgdbm-dev gawk fio dbench \
      uuid-runtime
 make
 make install
 sudo useradd fsgqa
 sudo useradd 123456-fsgqa
)

sudo /var/lib/jenkins/workspace/nova-build3/xfstests/check 2>&1 | tee ${NOVA_CI_LOG_DIR}/xfstests-results.out
./to_junit.py < ${NOVA_CI_LOG_DIR}/xfstests-results.out > ${NOVA_CI_LOG_DIR}/xfstests-results.xml
