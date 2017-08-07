#!/bin/bash

sudo apt-get install virtualenv pip
virtualenv venv
. venv/bin/activate
pip install pexpect
