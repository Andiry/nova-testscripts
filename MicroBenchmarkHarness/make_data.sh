#!/bin/bash

## SET ARGUMENTS HERE ##
dir="/mnt/ramdisk"                       ## directory where files are to be created
f=16                                      ## number of files to create
let block=(4 * 1024)                        ## block size. Default = 4 KB
let size=(2 * 1024 * 1024 * 1024)            ## size of each file. Default = 2G


echo "Creating $f files of size $size bytes in $dir..."
let n=($size/$block)

for i in $(seq 1 $f); do
    cmd="dd if=/dev/zero of=$dir/file$i bs=$block count=$n conv=fdatasync"
    echo $cmd
    $cmd
done


