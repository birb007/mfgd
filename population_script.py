import os
import concurrent.futures
from pathlib import Path
import subprocess
import sys
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mfgd.settings")
import django
django.setup()

from django.core.management import execute_from_command_line
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from mfgd_app.models import Repository, UserProfile, CanAccess

# Repository location
REPO_DIR = Path("repositories")

def create_profile(username, password, email="", is_admin=False):
    user, created = User.objects.get_or_create(
        username=username, email=email, password=make_password(password), is_superuser=is_admin
    )
    if created:
        user.save()
    profile, created = UserProfile.objects.get_or_create(user=user, isAdmin=is_admin)
    if created:
        profile.save()
    return profile


def create_repo(name, url, description, is_public, owner):
    path = (REPO_DIR / name).resolve()
    print(f'[*] cloning "{url}" into "{path}"')
    subprocess.run(["git", "clone", "-q", url, path], check=True)
    repo, created = Repository.objects.get_or_create(
        name=name, path=path, description=description, isPublic=is_public
    )
    if created:
        repo.save()
    return repo


def update_repo_perms(repo, users):
    for profile in users["manage"]:
        can_access = CanAccess.objects.get_or_create(
            user=profile, repo=repo, canManage=True
        )
    print(f'[ OK ] added managers to "{repo.name}"')
    for profile in users["view"]:
        can_access = CanAccess.objects.get_or_create(user=profile, repo=repo)
    print(f'[ OK ] added viewers to "{repo.name}"')


def populate():
    print("[*] creating users")
    users = create_users()
    print("[*] created all users")
    print("[*] cloning repositores")
    repositories = create_repositories(users)
    print("[*] cloned all repositories")
    print("[*] applying repository permissions")
    apply_permissions(repositories, users)
    print("[*] applied all permissions")


def create_users():
    users = {
        "birb": ("squawk", "bird@birdcage.info", True),
        "mate": ("not today", "mate@fsf.org", True),
        "paul": ("something idk", "paul@paulbeka.com"),
        "david": ("vs software goliath", "david@slingshots.r.us"),
        "geohot": ("lol @ s0ny", "geohot@fast.ai"),
        "linus": ("i hate cpp", "linus@kernel.org", True),
        "pasta": ("with pesto", "pasta@italy.it"),
        "vader": ("donate to your fsf", "vader@death.star"),
        "tom": ("has a mouse problem", "pestcontrol@jobs.com"),
        "enrique": ("did someone say wifi?", "pineapple@hak5.com"),
        "salad": ("hold the feta", "salad@kfc.info", True),
        "guido": ("python ru3lz", "guido@psf.org"),
        "orange": ("doesn't like blue", "tron-o@tron.mil"),
        "blue": ("doesn't like orange", "tron-b@tron.mil"),
        "bob": ("donate to your fsf", "vader@death.star"),
        "alice": ("i think i'm lost", "alice@wonderland.in", True),
        "mix": ("switching it up", "mix@blender.org"),
        "fruit": ("doctor a day", "fruit@fruitbowl.com"),
        "trepidation": ("literally shaking", "ms@money.mil"),
        "git": ("with pesto", "git@git.org"),
        "robocop": ("come quietly", "robocop@boston.dynamics.org"),
        "hal": ("hates humanity", "pestcontrol@jobs.com"),
        "sphinx": ("pyr4m1ds", "pineapple@hak5.com"),
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for name, profile in zip(users, executor.map(lambda t: create_profile(t[0], *t[1]), users.items())):
            users[name] = profile
            print(f"[ OK ] created profile \"{name}\"")
    return users


def create_repositories(users):
    repositories = {
        "mfgd": (
            "https://github.com/birb007/mfgd.git",
            "Self-hosted moderately friendly Git display written in Django.",
            False,
            users["vader"],
        ),
        "sauron": (
            "https://github.com/birb007/sauron.git",
            "Simple Intel VT-x type-2 hypervisor for 64-bit Linux.",
            True,
            users["birb"],
        ),
        "mcc": (
            "https://github.com/kukrimate/mcc.git",
            "[WIP] Project goal: C99 compiler.",
            True,
            users["mate"],
        ),
        "lambda": (
            "https://github.com/birb007/lambda.git",
            "λ-calculus calculus solver capable of β-reduction and α-conversion, written in C.",
            True,
            users["birb"]
        ),
        "momo_project": (
            "https://github.com/paulbeka/momo_project.git",
            "",
            True,
            users["paul"],
        ),
        "grr": (
            "https://github.com/kukrimate/grr.git",
            "Type-1 (bare-metal) AMD SVM hypervisor research project.",
            True,
            users["mate"],
        ),
        "sigma16-emulator": (
            "https://github.com/birb007/sigma16-emulator.git",
            "Alternative implementation of the research architecture Sigma16 with optional Python bindings and tooling.",
            False,
            users["birb"],
        ),
        "bank2Budget": (
            "https://github.com/paulbeka/bank2Budget.git",
            "Client non officiel pour consulter ses comptes chez ING Direct France",
            True,
            users["paul"],
        ),
        "bfjit": (
            "https://github.com/kukrimate/bfjit.git",
            "Brainfuck to AMD64 compiler",
            False,
            users["mate"],
        ),
        "IntelSpiInfo": (
            "https://github.com/kukrimate/IntelSpiInfo.git",
            "UEFI application for checking Intel SPI security.",
            False,
            users["mate"],
        ),
        "libefi": (
            "https://github.com/kukrimate/libefi.git",
            "Unix style UEFI development kit.",
            False,
            users["mate"],
        ),
        "python-http-server": (
            "https://github.com/kukrimate/python-http-server.git",
            "Simple, from-scratch HTTP/1.0 server I implemeneted as an assingment (NOTE: I developed this in git at the time, but only published long after the due date)",
            False,
            users["mate"],
        ),
        "veracity": (
            "https://github.com/birb007/veracity.git",
            "SAT solver implemented in Python.",
            False,
            users["birb"]
        ),
        "simple_exceptoins": (
            "https://github.com/birb007/simple_exceptions.git",
            "Simple exception handling using POSIX signals - published for convenience of access.",
            False,
            users["birb"],
        ),
        "garlic": (
            "https://github.com/birb007/garlic.git",
            "Asynchronous API wrapper for Onionoo, written in Python.",
            False,
            users["birb"],
        ),
    }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for repo in executor.map(
            lambda t: create_repo(t[0], *t[1]), repositories.items()
        ):
            try:
                repositories[repo.name] = repo
                print(f'[ OK ] cloned "{repo.name}" into "{repo.path}"')
            except:
                sys.exit(f'[ KO ] failed to clone "{repo.name}"')
    return repositories


def apply_permissions(repositories, users):
    permissions = {
        repositories["mfgd"]: {
            "manage": (users["birb"], users["mate"], users["paul"]),
            "view": (users["enrique"],),
        },
        repositories["mcc"]: {
            "manage": (users["mate"],),
            "view": (users["pasta"],),
        },
        repositories["momo_project"]: {
            "manage": (users["paul"],),
            "view": (users["birb"],),
        },
    }
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(
            lambda t: update_repo_perms(t[0], t[1]), permissions.items()
        )
    print("[*] all repository permissions applied")


if __name__ == "__main__":
    # Create new DB
    DB_FILE = Path("db.sqlite3")
    if DB_FILE.exists():
        DB_FILE.unlink()
    # Do migrations
    execute_from_command_line([ "manage.py", "migrate" ])

    if REPO_DIR.exists():
        if os.name == 'nt':
            # The proper API really doesn't like git's file permissions on
            # Windows, so we do this
            os.system(f"rmdir /S /Q {REPO_DIR}")
        else:
            shutil.rmtree(REPO_DIR)
    REPO_DIR.mkdir()

    # Main population script
    populate()
