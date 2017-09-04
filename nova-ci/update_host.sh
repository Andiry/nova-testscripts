#!/bin/bash

while true; do
    hn_ip=$(nmap -vvv -sn -oG - 172.16.52.0-255  | grep 'Status: Up' | grep -v '172.16.52.1 ' |grep -v '172.16.52.254' | cut -f 2 -d ' ')
    echo $hn_ip
    grep -v hn /private/etc/hosts > /tmp/hosts
    (cat /tmp/hosts; echo $hn_ip hn) > /private/etc/hosts
    cat /private/etc/hosts
    sleep 5
done
