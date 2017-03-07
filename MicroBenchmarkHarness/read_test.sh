#!/bin/bash

## USAGE 
## bash read_test.sh <number_of_threads> <number of iterations>
## Default is 16 threads, 5 iterations

n=$1

if [ -z $n ]; then
   n=16
fi

k=$2

if [ -z $k ]; then
   k=5
fi



for t in $(seq 1 $n); do
    for i in $(seq 1 $k); do
        ./file_rd.exe tc$t-size2GB-block4KB -tc $t -max $t -r 1
    done;
done
