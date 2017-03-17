#!/bin/sh

service mysql stop
umount /mnt/ramdisk
umount /mnt/scratch
umount /data1/mysql
rmmod nova
insmod nova.ko measure_timing=0 inplace_data_updates=1 replica_metadata=1 metadata_csum=1 unsafe_metadata=1 \
			wprotect=0 mmap_cow=1 data_csum=1 data_parity=1 dram_struct_csum=1

sleep 1

mount -t NOVA -o init /dev/pmem0 /data1/mysql
cp -rap /data1/mysql1/* /data1/mysql/
chown mysql.mysql /data1/*
chmod 700 /data1/mysql

service mysql start
