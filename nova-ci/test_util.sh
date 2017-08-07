#!/usr/bin/env bash

function clone_or_pull() {
    repo=$1
    dir=$(echo $repo | perl -ne '/github.com(:|\/)[\w-]+\/([-\w]+)/; print $2')

    if [ -d $dir ]; then
	(
	    cd $dir
	    git fetch 1>&2
	    git pull 1>&2
	)
    else
	git clone $repo  1>&2
    fi

    if [ ".$2" != "." ]; then
	cd $dir
	git checkout -b $2 1>&2
    fi
    
    echo $dir
}
