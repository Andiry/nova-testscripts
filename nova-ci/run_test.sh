 #!/usr/bin/env bash

DATE=$(date +"%F-%H-%M-%S.%N")
R=$PWD/results/$DATE
mkdir -p $R
CI_HOME=$HOME/nova-testscripts/nova-ci/

function get_kernel_version() {
    (cd $CI_HOME/linux-nova; 
	make kernelversion
	)

}

function get_packages() {
    sudo apt-get -y update
    sudo apt-get -y build-dep linux-image-$(uname -r) fakeroot
    sudo apt-get -y install make gcc emacs
}

function update_kernel () {
    pushd $CI_HOME
    git clone git@github.com:NVSL/linux-nova.git || (cd linux-nova; git pull)
    popd
}

function build_kernel () {
    pushd $CI_HOME
    cp ../kernel/gce.config ./linux-nova/.config
    (set -v;
	cd linux-nova; 
	make  deb-pkg LOCALVERSION=-nova
	) > $R/kernel_build.log
    popd
    KERNEL_VERSION=$(get_kernel_version)
}

function install_kernel() {
    KERNEL_VERSION=$(get_kernel_version)
    pushd $CI_HOME
    (cd $CI_HOME;
	sudo dpkg -i   linux-image-${KERNEL_VERSION}-${KERNEL_VERSION}-?_amd64.deb &&
	sudo dpkg -i linux-headers-${KERNEL_VERSION}-${KERNEL_VERSION}-?_amd64.deb) || false
}

function do_reboot() {
    echo Rebooting...
    exit 0
    #reboot
}

function build_module() {
    pushd $CI_HOME
    (set -v;
	cd linux-nova;
	make prepare
	make modules_prepare
	make SUBDIRS=scripts/mod
	make SUBDIRS=fs/nova
	cp fs/nova/nova.ko /lib/modules/${KERNEL_VERSION}/kernel/fs
	sudo depmod
	) |tee $R/module_build.log
    popd
    KERNEL_VERSION=$(get_kernel_version)
}

function update_and_build_nova() {
    pushd $CI_HOME
    if [ -d linux-nova ]; then
	cd linux-nova
	
	if git diff --name-only origin/master | grep -v fs/nova || 
	    ! [ -f /boot/vmlinuz-${KERNEL_VERSION}-* ]; then
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