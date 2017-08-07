export NOVA_CI_HOME=$HOME/nova-testscripts/nova-ci/
export NOVA_CI_LOG_DIR=$HOME/nova-testscripts/nova-ci/results/
export NOVA_CI_PRIMARY_FS=/mnt/ramdisk
export NOVA_CI_SECONDARY_FS=/mnt/scratch
export NOVA_CI_PRIMARY_DEV=/dev/pmem0
export NOVA_CI_SECONDARY_DEV=/dev/pmem1

cd $NOVA_CI_HOME

. test_util.sh

K_SUFFIX=nova

function update_self {
    git fetch
    git checkout master
}

function get_kernel_version() {
    make kernelversion | perl -ne 'chop;print'
    echo -${K_SUFFIX}
}

function count_cpus() {
    cat /proc/cpuinfo  | grep processor | wc -l
}

function update_kernel() {
    config=$1
    shift
    repo=$1
    shift
    branch=$1
    shift

    echo $repo
    dir=$(clone_or_pull $repo)
    echo $dir
    cd $dir
    git checkout $branch
    cp ../../kernel/$config ./.config
    yes "" | make oldconfig
}

function build_kernel() {
    sudo rm -rf *.tar.gz *.dsc *.deb *.changes
    cd linux-nova;
    make -j$[$(count_cpus) + 1] deb-pkg LOCALVERSION=-${K_SUFFIX};
}

function install_kernel() {
    KERNEL_VERSION=$(cd linux-nova; get_kernel_version)
    sudo dpkg -i linux-image-${KERNEL_VERSION}_${KERNEL_VERSION}-?_amd64.deb
    sudo dpkg -i linux-headers-${KERNEL_VERSION}_${KERNEL_VERSION}-?_amd64.deb
    sudo dpkg -i linux-image-${KERNEL_VERSION}-dbg_${KERNEL_VERSION}-?_amd64.deb
    sudo update-grub
}

function compute_grub_default() {
    KERNEL_VERSION=$(cd linux-nova; get_kernel_version)
    menu=$(grep 'menuentry ' /boot/grub/grub.cfg  | grep -n $KERNEL_VERSION| grep -v recovery |grep -v  upstart | cut -f 1 -d :)
    menu=$[menu-2]
    echo "1>$menu"
}

function reboot_to_nova() {
    sudo grub-reboot $(compute_grub_default)
    sudo systemctl reboot -i
}

function check_pmem() {
    if  ! [ -e /dev/pmem0 -a -e /dev/pmem1 ]; then
	echo missing
    else
	echo ok
    fi
}

function load_nova() {
    sudo modprobe libcrc32c
    sudo rmmod nova
    sudo modprobe nova $*
    sleep 1
}

function mount_nova() {
    mount_one $NOVA_CI_PRIMARY_DEV $NOVA_CI_PRIMARY_FS
    mount_one $NOVA_CI_SECONDARY_DEV $NOVA_CI_SECONDARY_FS
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

function run-test() {
    dir=$1
    shift
    (cd $dir;
     echo ./go.sh $*
     REBUILD=yes ./go.sh $*
    )
}
