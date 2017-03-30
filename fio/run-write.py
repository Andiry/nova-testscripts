#!/usr/bin/python

import re
import sys
import os
import time

def main():
	os.system("fio fio-write-1")
	os.system("fio fio-write-2")
	os.system("fio fio-write-4")
	os.system("fio fio-write-8")
	os.system("fio fio-write-16")
	print "done."
	return

main()
