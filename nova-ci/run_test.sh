#!/usr/bin/env bash

DATE=$(date +"%F-%H-%M-%S.%N")
R=$PWD/results/$DATE
mkdir -p $R
CI_HOME=$HOME/nova-testscripts/nova-ci/

function get_packages() {
    sudo apt-get -y update
    sudo apt-get -y build-dep linux-image-$(uname -r) fakeroot
    sudo apt-get -y install make gcc
}

function update_kernel () {
    pushd $CI_HOME
    git clone git@github.com:NVSL/linux-nova.git || (cd linux-nova; git pull)
    popd
}

function build_kernel () {
    pushd $CI_HOME
    cp ../kernel/gce.config ./linux-nova/.config
    (cd linux-nova; 
	make  deb-pkg LOCALVERSION=-nova
	) > $R/kernel_build.log
    popd
}

function install_kernel() {
    pushd $CI_HOME
    (sudo dpkg -i linux-image-*-nova_4.10.0-rc8-nova-2_amd64.deb && sudo dpkg -i linux-headers-*-rc8-nova_4.10.0-rc8-nova-2_amd64.deb) || return 1
    popd
}

function do_reboot() {
    echo Rebooting...
    reboot
}

function build_module() {
    pushd $CI_HOME
    (cd linux-nova;
	make prepare
	make modules_prepare
	make SUBDIRS=scripts/mod
	make SUBDIRS=fs/nova
	cp drivers/staging/ft1000/ft1000-usb/ft1000.ko /lib/modules/3.2.0-4-686-pae/kernel/drivers/staging/
	depmod
	) > $R/module_build.log
    popd
}

function update_and_build_nova() {
    pushd $CI_HOME
    if [ -d linux-nova ]; then
	cd linux-nova
	
	if git diff --name-only origin/master | grep -v fs/nova; then
	    git pull
	    build_kernel
	    if install_kernel; then
		reboot
	    else
		echo "Install failed"
	    fi
	else
	    git pull
	    build_module
	fi
    else
	git clone git@github.com:NVSL/linux-nova.git
	cd linux-nova
	build_kernel
    fi
    popd 
}


#get_packages()
#build_module()