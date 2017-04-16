#!/bin/bash

watch -n 0.5 "df | grep 'Filesystem\|pmem0'; echo; \
              ls -l /mnt/ramdisk/; echo; \
              sudo fuser -uvm /mnt/ramdisk"
