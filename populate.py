import os
import concurrent.futures
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mfgd.settings")
import django

django.setup()
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from mfgd_app.models import Repository, UserProfile, CanAccess


# create repository folder
REPO_DIR = Path("repositories")
if REPO_DIR.exists():
    sys.exit("[ KO ] repositories directory already exists, exiting...")
REPO_DIR.mkdir()


def create_profile(username, password, email="", is_admin=False):
    user, created = User.objects.get_or_create(
        username=username, email=email, password=make_password(password)
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
        "richard": ("GNU/Linux", "rms@gnu.org"),
        "birb": ("squawk", "bird@birdcage.info", True),
        "mate": ("soylicious", "mate@fsf.org", True),
        "paul": ("something idk", "paul@paulbeka.com"),
        "luke": ("bugman", "luke@lukesmith.xyz"),
        "david": ("vs software goliath", "david@slingshots.r.us"),
        "geohot": ("lol @ s0ny", "geohot@fast.ai"),
        "linus": ("i hate cpp", "linus@kernel.org"),
        "pasta": ("with pesto", "pasta@italy.it"),
        "vader": ("donate to your fsf", "vader@death.star"),
        "tom": ("has a mouse problem", "pestcontrol@jobs.com"),
        "enrique": ("did someone say wifi?", "pineapple@hak5.com"),
        "salad": ("hold the feta", "salad@kfc.info"),
        "guido": ("python ru3lz", "guido@psf.org"),
        "orange": ("doesn't like blue", "tron-o@tron.mil"),
        "blue": ("doesn't like orange", "tron-b@tron.mil"),
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
            users["richard"],
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
            False,
            users["mate"],
        ),
        "momo_project": (
            "https://github.com/paulbeka/momo_project.git",
            "",
            True,
            users["paul"],
        ),
        "based.cooking": (
            "https://github.com/LukeSmithxyz/based.cooking.git",
            "A simple culinary website.",
            True,
            users["luke"],
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
            "view": (users["luke"],),
        },
        repositories["mcc"]: {
            "manage": (users["mate"],),
            "view": (),
        },
        repositories["momo_project"]: {
            "manage": (users["paul"],),
            "view": (users["birb"], users["richard"]),
        },
        repositories["based.cooking"]: {
            "manage": (users["luke"], users["richard"]),
            "view": (users["mate"], users["paul"], users["birb"]),
        },
    }
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(
            lambda t: update_repo_perms(t[0], t[1]), permissions.items()
        )
    print("[*] all repository permissions applied")


if __name__ == "__main__":
    populate()
