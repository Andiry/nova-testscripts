#!/usr/bin/env bash -v

. $NOVA_CI_HOME/test_util.sh

export XFSTESTS=$(clone_or_pull git@github.com:NVSL/xfstests.git hacked-for-gce)

export FSTYP=NOVA
export TEST_DEV=$NOVA_CI_PRIMARY_DEV
export TEST_DIR=$NOVA_CI_PRIMARY_FS
export SCRATCH_DEV=$NOVA_CI_SECONDARY_DEV
export SCRATCH_MNT=$NOVA_CI_SECONDARY_FS

#echo $XFSTESTS

set -v

cd $XFSTESTS
if [ ".yes" == ".$REBUILD" ] || ! [ -d /var/lib/xfstests ] ; then
    sudo apt-get install -y xfslibs-dev uuid-dev libtool-bin \
	 e2fsprogs automake gcc libuuid1 quota attr libattr1-dev make \
	 libacl1-dev libaio-dev xfsprogs libgdbm-dev gawk fio dbench \
	 uuid-runtime
    
    make
    sudo make install
    sudo useradd fsgqa
    sudo useradd 123456-fsgqa
fi

pwd

sudo FSTYP=NOVA TEST_DEV=$NOVA_CI_PRIMARY_DEV TEST_DIR=$NOVA_CI_PRIMARY_FS SCRATCH_MNT=$NOVA_CI_SECONDARY_FS SCRATCH_DEV=$NOVA_CI_SECONDARY_DEV bash  ./check $* 2>&1 | tee ${NOVA_CI_LOG_DIR}/xfstests-results.out
sudo ./to_junit.py < ${NOVA_CI_LOG_DIR}/xfstests-results.out > ${NOVA_CI_LOG_DIR}/xfstests-results.xml


