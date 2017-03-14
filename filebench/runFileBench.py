#!/usr/bin/python

import commands,re

def benchmark(cmd) :
    status, res = commands.getstatusoutput(cmd)

    if status != 0 :
        print "filebench failed with status ", status
        print res
        exit(1)

    searchObj = re.search( r'(\d*\.\d+|\d+) ops/s', res, )
    return searchObj.group(1)

print "Running fileserver.."
t1 = benchmark("filebench -f fileserver.f")
print "Running varmail.."
t2 = benchmark("filebench -f varmail.f")
print "Running webproxy.."
t3 = benchmark("filebench -f webproxy.f")
print "Running webserver.."
t4 = benchmark("filebench -f webserver.f")

print "fileserver\tvarmail\twebproxy\twebserver\t"
print t1,
print "\t",
print t2,
print "\t",
print t3,
print "\t",
print t4
