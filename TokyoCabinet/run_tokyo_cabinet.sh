#!/bin/bash

rm -rf /mnt/ramdisk/*
./tokyo_cabinet_set --iterations=1 --num_keys=50000 --key_size=8 --value_size=1024 --pmem_mode=0
