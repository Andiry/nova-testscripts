#!/bin/bash

rm -rf /mnt/ramdisk/*
./tokyo_cabinet_set --iterations=3 --num_keys=1000000 --key_size=8 --value_size=1024 --pmem_mode=1 --fallocate=1
