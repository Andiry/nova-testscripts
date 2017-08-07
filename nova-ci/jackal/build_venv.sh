#!/bin/bash

sudo apt-get install virtualenv
virtualenv venv
. venv/bin/activate
pip install pexpect
