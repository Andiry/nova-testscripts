
function init_tests() {
    
    export NOVA_CI_DATE=$(date +"%F-%H-%M-%S.%N")
    R=$PWD/results/$NOVA_CI_DATE
    mkdir -p $R
    export NOVA_CI_LOG_DIR=$PWD/results/latest
    ln -sf $R  ${NOVA_CI_LOG_DIR}  
    
    export NOVA_CI_HOME=$HOME/nova-testscripts/nova-ci/
    K_SUFFIX=nova

    export NOVA_CI_PRIMARY_FS=/mnt/ramdisk
    export NOVA_CI_SECONDARY_FS=/mnt/scratch
    export NOVA_CI_PRIMARY_DEV=/dev/pmem0
    export NOVA_CI_SECONDARY_DEV=/dev/pmem1

    export NOVA_CI_KERNEL_NAME=$(get_kernel_version)

    export KERNEL_VERSION=$(get_kernel_version)

}

function count_cpus() {
    cat /proc/cpuinfo  | grep processor | wc -l
}

function get_kernel_version() {
    (
	cd $NOVA_CI_HOME/linux-nova; 
	make kernelversion | perl -ne 'chop;print'
	echo -${K_SUFFIX}
    )
}


function compute_grub_default() {
    menu=$(grep 'menuentry ' /boot/grub/grub.cfg  | grep -n $KERNEL_VERSION| grep -v recovery | cut -f 1 -d :)
    menu=$[menu-2]
    echo "1>$menu"
}

function get_packages() {
    sudo apt-get -y update
    sudo apt-get -y build-dep linux-image-$(uname -r) fakeroot
    sudo apt-get -y install make gcc emacs
}

function update_kernel () {
    pushd $NOVA_CI_HOME
    git clone git@github.com:NVSL/linux-nova.git || (cd linux-nova; git pull)
    popd
}

function build_kernel () {
    pushd $NOVA_CI_HOME
    cp ../kernel/gce.config ./linux-nova/.config
    sudo rm -rf *.tar.gz *.dsc *.deb *.changes
    (
	set -v;
	cd linux-nova; 
	make -j$[$(count_cpus) + 1] deb-pkg LOCALVERSION=-${K_SUFFIX};
	) 2>&1 | tee $R/kernel_build.log 
    popd
}

function install_kernel() {

    pushd $NOVA_CI_HOME
    (
	set -v;
	cd $NOVA_CI_HOME;
	sudo dpkg -i   linux-image-${KERNEL_VERSION}_${KERNEL_VERSION}-?_amd64.deb &&
	sudo dpkg -i linux-headers-${KERNEL_VERSION}_${KERNEL_VERSION}-?_amd64.deb
	) || false
    sudo update-grub
}

function reboot_to_nova() {
    echo Rebooting to $(compute_grub_default)...
    sudo grub-reboot $(compute_grub_default)
    sudo systemctl reboot -i
}

function build_module() {
    pushd $NOVA_CI_HOME
    (set -v;
	cd linux-nova;
	make prepare
	make modules_prepare
	make SUBDIRS=scripts/mod
	make SUBDIRS=fs/nova
	sudo cp fs/nova/nova.ko /lib/modules/${KERNEL_VERSION}/kernel/fs
	sudo depmod
	) |tee $R/module_build.log
    popd

}

function build_and_reboot() {
    build_kernel
    if install_kernel; then
	reboot_to_nova
    else
	echo "Install failed"
    fi
}


function update_and_build_nova() {
    pushd $NOVA_CI_HOME
    if [ -d linux-nova ]; then
	cd linux-nova
	
	if git diff --name-only origin/master | grep -v fs/nova || 
	    ! [ -f /boot/vmlinuz-${KERNEL_VERSION}-* ]; then
	    echo Main kernel is out of date or missing
	    git diff --name-only origin/master
	    ls /boot/*
	    
	    git pull
	    build_and_reboot
	else
	    git pull
	    build_module
	fi
    else
	echo Linux sources missing
	git clone git@github.com:NVSL/linux-nova.git
	if [ -d linux-nova ]; then
	    cd linux-nova
	    build_and_reboot
	else
	    echo git failed
	fi
    fi
    popd 
}


function mount_nova() {
    
    sudo umount $NOVA_CI_SECONDARY_FS
    sudo umount $NOVA_CI_PRIMARY_FS
    

    load_nova
    
    sudo mkdir -p $NOVA_CI_PRIMARY_FS
    sudo mkdir -p $NOVA_CI_SECONDARY_FS
    
    
    sudo mount -t NOVA -o init $NOVA_CI_PRIMARY_DEV $NOVA_CI_PRIMARY_FS
    sudo mount -t NOVA -o init $NOVA_CI_SECONDARY_DEV $NOVA_CI_SECONDARY_FS
}

function remount_nova() {
    sudo umount $NOVA_CI_SECONDARY_FS
    sudo umount $NOVA_CI_PRIMARY_FS
    
    sudo mount -t NOVA $NOVA_CI_PRIMARY_DEV $NOVA_CI_PRIMARY_FS
    sudo mount -t NOVA $NOVA_CI_SECONDARY_DEV $NOVA_CI_SECONDARY_FS
}

function load_nova() {
    
    sudo modprobe libcrc32c
    sudo rmmod nova
    sudo modprobe nova measure_timing=0 \
	 inplace_data_updates=0 \
	 wprotect=0 mmap_cow=1 \
	 unsafe_metadata=1 \
	 replica_metadata=1 metadata_csum=1 dram_struct_csum=1 \
	 data_csum=1 data_parity=1
    
    sleep 1


}


function run_tests() {
    if [ ".$1" = "." ]; then
	targets=$(cat ${NOVA_CI_HOME}/tests_to_run.txt)
    else
	targets=$1
	shift
    fi
    
    for i in $targets; do
	(cd $i;
	 mount_nova
	 bash -v ./go.sh $*
	) 2>&1 | tee ${NOVA_CI_LOG_DIR}/$i.log
    done
}
