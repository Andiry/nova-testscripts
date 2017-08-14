#!/usr/bin/env bash

function clone_or_pull() {
    repo=$1
    dir=$(echo $repo | perl -ne '/github.com(:|\/)[\w-]+\/([-\w]+)/; print $2')

    echo repo=$repo 1>&2
    echo dir=$dir 1>&2
    
    if ! [ -d $dir ]; then
	git clone $repo  1>&2
    fi
    (
	cd $dir
	for branch in `git branch -a | grep remotes | grep -v HEAD | grep -v master `; do
	    git branch --track ${branch#remotes/origin/} $branch
	done;
	git fetch --all 
	git pull 
    ) 1>&2

    if [ ".$2" != "." ]; then
	(
	    cd $dir
	    git checkout $2 1>&2
	)
    fi
    
    echo $dir
}
