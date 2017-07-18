#!/usr/bin/bash

export LOOPBACK_CRASH=yes
./run_tests.sh ltp -f nova-empty
