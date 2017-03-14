#!/bin/bash

rm -rf /mnt/ramdisk/mongodb
mkdir /mnt/ramdisk/mongodb
numactl --interleave=all mongod --dbpath /mnt/ramdisk/mongodb --storageEngine mmapv1 &
export MONGO_PID=$!
echo "MONGOD PID is "
echo $MONGO_PID
./bin/ycsb load mongodb-async -s -P workloads/workloada -threads $1 > asyncLoad
./bin/ycsb run  mongodb-async -s -P workloads/workloada -threads $1 > asyncRun
kill -9 $MONGO_PID
perl getNum.pl asyncLoad asyncRun >> results
