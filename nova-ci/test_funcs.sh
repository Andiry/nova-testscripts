
function init_tests() {

    #set -v
    export NOVA_CI_DATE=$(date +"%F-%H-%M-%S.%N")
    R=$PWD/results/$NOVA_CI_DATE
    mkdir -p $R
    export NOVA_CI_LOG_DIR=$PWD/results/latest
    rm ${NOVA_CI_LOG_DIR}
    ln -sf $R  ${NOVA_CI_LOG_DIR}  
    
    export NOVA_CI_HOME=$HOME/nova-testscripts/nova-ci/
    K_SUFFIX=nova

    export NOVA_CI_PRIMARY_FS=/mnt/ramdisk
    export NOVA_CI_SECONDARY_FS=/mnt/scratch
    export NOVA_CI_PRIMARY_DEV=/dev/pmem0
    export NOVA_CI_SECONDARY_DEV=/dev/pmem1

    export NOVA_CI_KERNEL_NAME=$(get_kernel_version)

    export KERNEL_VERSION=$(get_kernel_version)
    echo "module nova +p" | sudo tee /sys/kernel/debug/dynamic_debug/control
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


function get_host_type() {
    if ps aux | grep -q google_clock_skew_deamon; then
	echo gce
    else
	echo ubuntu
    fi
}

function compute_grub_default() {
    menu=$(grep 'menuentry ' /boot/grub/grub.cfg  | grep -n $KERNEL_VERSION| grep -v recovery |grep -v  upstart | cut -f 1 -d :)
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
    cp ../kernel/$(get_host_type).config ./linux-nova/.config
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

function build_nova() {
    pushd $NOVA_CI_HOME
    (set -v;
	cd linux-nova;
	make LOCALVERSION=-${K_SUFFIX} prepare 
	make LOCALVERSION=-${K_SUFFIX} modules_prepare 
	make SUBDIRS=scripts/mod LOCALVERSION=-${K_SUFFIX}
	make -j$[$(count_cpus) + 1] SUBDIRS=fs/nova LOCALVERSION=-${K_SUFFIX}
	sudo cp fs/nova/nova.ko /lib/modules/${KERNEL_VERSION}/kernel/fs
	sudo depmod
	) 2>&1 |tee $R/module_build.log
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

function list_module_args() {
    if [ "." = "$1." ]; then
	modules=$(cat /proc/modules | cut -f 1 -d " ")
    else
	modules=$@
    fi
    for module in $modules; do 
	echo "$module ";
	if [ -d "/sys/module/$module/parameters" ]; then
	    ls /sys/module/$module/parameters/ | while read parameter; do
		echo -n "$parameter=";
		cat /sys/module/$module/parameters/$parameter;
	    done;
	fi;
	echo;
    done
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
	    build_nova
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

function umount_nova() {
    sudo umount $NOVA_CI_SECONDARY_FS
    sudo umount $NOVA_CI_PRIMARY_FS
}


function mount_one() {
    local dev=$1
    local dir=$2

    sudo mkdir -p $dir
    sudo mount -t NOVA -o init $dev $dir
}


function mount_nova() {

    umount_nova
    
    reload_nova

    mount_one $NOVA_CI_PRIMARY_DEV $NOVA_CI_PRIMARY_FS
    mount_one $NOVA_CI_SECONDARY_DEV $NOVA_CI_SECONDARY_FS
}

function remount_nova() {
    sudo umount $NOVA_CI_SECONDARY_FS
    sudo umount $NOVA_CI_PRIMARY_FS
    
    sudo mount -t NOVA $NOVA_CI_PRIMARY_DEV $NOVA_CI_PRIMARY_FS
    sudo mount -t NOVA $NOVA_CI_SECONDARY_DEV $NOVA_CI_SECONDARY_FS
}

function reload_nova() {

    protect="replica_metadata=1 metadata_csum=1 dram_struct_csum=1 
	data_csum=1 data_parity=1"
        protect=""
    
    args="measure_timing=0 
	inplace_data_updates=0 
	wprotect=0 mmap_cow=1 
	unsafe_metadata=0 
	$protect"

    sudo modprobe libcrc32c
    sudo rmmod nova

    sudo modprobe nova $args
    
    sleep 1


}

function load_bisection() {
    umount_nova
    pushd $NOVA_CI_HOME/linux-nova/fs/nova;
    local dir=$NOVA_CI_HOME/bisect_modules
    sudo cp $dir/$1-*.ko /lib/modules/${KERNEL_VERSION}/kernel/fs/nova.ko
    sudo depmod
    popd
    reload_nova
}

function build_bisection () {
    set -v
    local dir=$NOVA_CI_HOME/bisect_modules
    mkdir -p $dir
    rm -rf $dir/*.{ko,build}

    pushd $NOVA_CI_HOME/linux-nova/fs/nova;
    local c=0;
    for i in $(git log $1 | grep ^commit | cut -f 2 -d ' ' |tac ); do
	local name=$(printf "%03d" $c)-$i
	echo $name
	(git checkout $i; build_nova) 2>&1 | tee $dir/$name.build;
	cp nova.ko $dir/$name.ko
	c=$[c+1]
    done
    popd
}

function start_dmesg_record() {
    stop_dmesg_record >/dev/null 2>&1 
    sudo dmesg -C
    t=$(sudo bash -c "dmesg --follow > $1 & echo \$!")
    DMESG_RECORDER=$t
}

function stop_dmesg_record() {
    sudo kill $DMESG_RECORDER
}

function dmesg_to_serial() {
    dmesg -w | sudo tee /dev/ttyS1 > /dev/null
}


function do_run_tests() {
    if [ ".$1" = "." ]; then
	targets=$(cat ${NOVA_CI_HOME}/tests_to_run.txt)
    else
	targets=$1
	shift
    fi

    (
	for i in $targets; do
	    (cd $i;
	     start_dmesg_record  ${NOVA_CI_LOG_DIR}/$i.dmesg
	     mount_nova
	     bash -v ./go.sh $*
	     stop_dmesg_record
	    ) 2>&1 | tee ${NOVA_CI_LOG_DIR}/$i.log
	done
    ) 2>&1 | tee  $NOVA_CI_LOG_DIR/run_test.log
}
