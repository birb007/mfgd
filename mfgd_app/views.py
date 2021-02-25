import binascii

from django.http import HttpResponse
from django.shortcuts import render
from pathlib import Path
import pygit2

from mfgd_app import utils
from mfgd_app.types import ObjectType, TreeEntry

# Directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Repo
repo = pygit2.Repository(BASE_DIR / ".git")


def index(request):
    return HttpResponse("this is the index page", content_type="text/plain")

def read_blob(blob):
    MAX_BLOB_SIZE = 100 * 1 << 10   # 100K

    content = blob.data
    if blob.is_binary:
        if blob.size > MAX_BLOB_SIZE:
            return "blob_binary.html", ""
        return "blob_binary.html", utils.hex_dump(content)
    else:
        if blob.size > MAX_BLOB_SIZE:
            return "blob.html", ""
    return "blob.html", content.decode()

def gen_branches(oid):
    class Branch:
        def __init__(self, name, url):
            self.name = name
            self.url = url

    l = list(repo.branches.local)
    if oid not in l:
        l.append(oid)

    return [ Branch(name, "/view/" + name) for name in l ]

def gen_crumbs(path):
    class Crumb:
        def __init__(self, name, url):
            self.name = name
            self.url = url
        def __str__(self):
            return self.name

    crumbs = []
    for part in utils.split_path(path):
        crumbs.append(Crumb(part, "/".join(crumbs)))
    return crumbs

def gen_branches(oid):
    class Branch:
        def __init__(self, name, url):
            self.name = name
            self.url = url

    l = list(repo.branches.local)
    if oid not in l:
        l.append(oid)

    return [ Branch(name, "/view/" + name) for name in l ]


def gen_crumbs(path):
    class Crumb:
        def __init__(self, name, url):
            self.name = name
            self.url = url
        def __str__(self):
            return self.name

    crumbs = []
    for part in utils.split_path(path):
        crumbs.append(Crumb(part, "/".join(crumbs)))
    return crumbs


def view(request, oid, path):
    # First we normalize the path so libgit2 doesn't choke
    path = utils.normalize_path(path)

    # Find commit in the repo
    target = utils.find_branch_or_commit(repo, oid)
    if target is None:
        return HttpResponse("Invalid commit ID")

    # Resolve path inside commit
    obj = utils.resolve_path(target.tree, path)
    if obj == None:
        return HttpResponse("Invalid path")

    context = { "oid": oid,
                "path": path,
                "branches": gen_branches(oid),
                "crumbs": gen_crumbs(path),
                }
    # Display correct template
    if obj.type == ObjectType.TREE:
        template = "tree.html"
        context["entries"] = utils.tree_entries(repo, target, obj, path)
    elif obj.type == ObjectType.BLOB:
        template, context["code"] = read_blob(obj)
    else:
        return HttpResponse("Unsupported object type")

    return render(request, template, context=context)
