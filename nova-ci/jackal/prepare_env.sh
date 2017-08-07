#!/bin/bash

gcloud config set compute/zone us-west1-c
gcloud config set compute/region us-west1

sudo apt-get install virtualenv pip
virtualenv venv
. venv/bin/activate
pip install pexpect
