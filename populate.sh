#!/bin/bash
rm -rf repositories
rm -f db.sqlite3
python3 manage.py migrate
python3 populate.py
