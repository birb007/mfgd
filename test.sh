#!/bin/bash

TEST_REPO=tests/repo

[ -d $TEST_REPO/simple ] || git init $TEST_REPO/simple
python3 manage.py test
