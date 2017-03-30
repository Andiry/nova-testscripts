#!/usr/bin/python

import re
import sys
import os
import time

def main():
	os.system("echo 1 > /proc/sys/vm/drop_caches")
	os.system("fio fio-read-1")
	os.system("echo 1 > /proc/sys/vm/drop_caches")
	os.system("fio fio-read-2")
	os.system("echo 1 > /proc/sys/vm/drop_caches")
	os.system("fio fio-read-4")
	os.system("echo 1 > /proc/sys/vm/drop_caches")
	os.system("fio fio-read-8")
	os.system("echo 1 > /proc/sys/vm/drop_caches")
	os.system("fio fio-read-16")
	print "done."
	return

main()
