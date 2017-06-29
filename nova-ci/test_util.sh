#!/usr/bin/env bash

function clone_or_pull() {
    repo=$1
    dir=$(echo $repo | perl -ne '/github.com(:|\/)[\w-]+\/([-\w]+)/; print $2')

    https://github.com/NVSL/linux-nova.git
    git@github.com:NVSL/linux-nova.git
    
    if [ -d $dir ]; then
	cd $dir
	git pull
    else
	git clone $repo
    fi
    echo $dir
}
