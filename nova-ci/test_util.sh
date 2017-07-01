#!/usr/bin/env bash

function clone_or_pull() {
    repo=$1
    dir=$(echo $repo | perl -ne '/github.com(:|\/)[\w-]+\/([-\w]+)/; print $2')

    if [ -d $dir ]; then
	(
	    cd $dir
	    git fetch > /dev/null 2>&1
	    git pull > /dev/null  2>&1
	)
    else
	git clone $repo  >/dev/null  2>&1
    fi

    if [ ".$2" != "." ]; then
	cd $dir
	git checkout -b $2 >/dev/null 2>&1 
    fi
    
    echo $dir
}
