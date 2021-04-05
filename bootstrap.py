import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mfgd.settings")
import django
django.setup()

from django.core.management import execute_from_command_line
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from mfgd_app.models import UserProfile

def main():
    DATABASE = Path("db.sqlite3")
    if DATABASE.exists():
        sys.exit("database already exists, have you already bootstrapped?")
    execute_from_command_line(["manage.py", "migrate"])
    execute_from_command_line(["manage.py", "createsuperuser"])
    UserProfile.objects.create(user=User.objects.all()[0], isAdmin=True)

if __name__ == "__main__":
    main()
