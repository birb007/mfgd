#!/bin/bash

TEST_REPO_DIR=tests/repo
REPO_LINEAR=$TEST_REPO_DIR/linear
REPO_SIMPLE=$TEST_REPO_DIR/simple
REPO_N_MERGE=$TEST_REPO_DIR/n_merge
REPO_DIRS=$TEST_REPO_DIR/dirs

# create simple repository
#   consists of no files
[ -d $REPO_SIMPLE ] || git init $REPO_SIMPLE

# create linear repository
#   includes several linear commits
if [ ! -d $REPO_LINEAR ]; then
    git init $REPO_LINEAR
    pushd $REPO_LINEAR
    for i in {1..5}; do
        printf "#${i}\nmulti\nline\nfile" > file
        git add file
        git commit -m "commit #$i"
    done
    popd
fi

if [ ! -d $REPO_N_MERGE ]; then
    git init $REPO_N_MERGE
    pushd $REPO_N_MERGE
    echo "#1" >> file
    git add file
    git commit -m "commit #1"
    echo "#2" >> file
    git commit -a -m "commit #2"
    echo "#3" >> file
    git commit -a -m "commit #3"
    git checkout -b stage
    echo "#4" > file.new
    cat file >> file.new
    mv file.new file
    git commit -a -m "commit #4"
    git checkout master
    echo "#5" >> file
    git commit -a -m "commit #5"
    git checkout stage
    echo "#6" > file.new
    cat file >> file.new
    mv file.new file
    git commit -a -m "commit #6"
    git checkout master
    git merge stage --no-edit
    popd
fi

if [ ! -d $REPO_DIRS ]; then
    git init $REPO_DIRS
    pushd $REPO_DIRS
    echo "#1" > file1
    git add .
    git commit -m "add file1"
    echo "#2" > file2
    git add .
    git commit -m "add file2"
    mkdir dir1
    touch dir1/.keep
    git add .
    git commit -m "add dir1"
    mkdir dir2
    touch dir2/.keep
    git add .
    git commit -m "add dir2"
    popd
fi

python3 manage.py test
