#!/usr/bin/bash

host=$1
shift
while ! ssh $host true; do
    echo Retrying $1 
    sleep 1;
done

ssh $host 
