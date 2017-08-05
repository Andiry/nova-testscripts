#!/bin/bash

host=$1
shift

# clear out known_hosts.  Otherwise, when google recycles IPs, we get failures
# and ssh becomes interactive.
touch ~/.ssh/known_hosts
cp ~/.ssh/known_hosts ~/.ssh/known_hosts.bak
grep -v $host < ~/.ssh/known_hosts.bak > ~/.ssh/known_hosts

# automatically connect to unknown hosts, and don't hash so the grep above works.
while ! ssh -o StrictHostKeyChecking=no -o HashKnownHosts=no $host true; do
    echo Retrying $1 
    sleep 1;
done

ssh $host 
