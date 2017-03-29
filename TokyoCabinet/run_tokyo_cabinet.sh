#!/bin/bash

rm -rf /mnt/ramdisk/*
cp tokyo_cabinet_set /mnt/ramdisk/
cd /mnt/ramdisk
./tokyo_cabinet_set
