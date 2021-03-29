#!/bin/bash
rm -rf repositories
rm -f db.sqlite3
python manage.py migrate
python populate.py
