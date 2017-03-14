#!/bin/bash

rm -rf /mnt/ramdisk/mongodb
mkdir /mnt/ramdisk/mongodb
numactl --interleave=all mongod --dbpath /mnt/ramdisk/mongodb --storageEngine mmapv1 &
export MONGO_PID=$!
echo "MONGOD PID is "
echo $MONGO_PID
./bin/ycsb load mongodb -s -P workloads/workloada -threads $1 > syncLoad
./bin/ycsb run  mongodb -s -P workloads/workloada -threads $1 > syncRun
kill -9 $MONGO_PID
perl getNum.pl syncLoad syncRun >> results
