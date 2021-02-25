from django.http import HttpResponse
from django.shortcuts import render
from pathlib import Path
import pygit2

from mfgd_app import utils
from mfgd_app.types import ObjectType, StaticEntry

# Directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Repo
repo = pygit2.Repository(BASE_DIR / ".git")


def format_author(commit):
    return "%s <%s>" % (commit.author.name, commit.author.email)

def str_tree(tree, indent=0):
    r = ""
    for obj in tree:
        r += "  " * indent + obj.name + "\n"
        if obj.type_str == "tree":
            r += str_tree(obj, indent + 1)
    return r

def index(request):
    branch = next(iter(repo.branches.local))
    branch_ref = repo.references["refs/heads/%s" % branch]

    r = ""
    for commit in repo.walk(branch_ref.target, pygit2.GIT_SORT_TOPOLOGICAL):
        r += "%s\n%s\n%s\n" % (commit.oid, format_author(commit), commit.message)
        r += str_tree(commit.tree)
        r += "\n"

    return HttpResponse(r, content_type="text/plain")

def find_branch_or_commit(ident):
    try:
        obj = repo.get(ident)
        if obj.type_str != "commit":
            raise ValueError()
        return obj
    except:
        try:
            branch_ref = repo.references["refs/heads/%s" % ident]
            return repo.get(branch_ref.target)
        except:
            return None

def tree(request, commit, path):
    context = {}

    tree_entries = utils.resolve_path(obj.tree, path)
    if tree_entries is None or tree_entries.type != ObjectType.TREE:
        return HttpResponse("invalid path")

    clean_entries = []
    for entry in tree:
        change = utils.get_file_history(repo, target.id, path + entry.name)
        wrapper = StaticEntry(entry.name, entry.type, change)
        clean_entries.append(wrapper)
    return clean_entries

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

    context = { "oid": oid, "path": path }
    # Display correct template
    if obj.type == ObjectType.TREE:
        template = "tree.html"
        context["entries"] = tree_entries(target, obj, path)
    elif obj.type == ObjectType.BLOB:
        template = "blob.html"
        context["code"] = obj.data.decode()
    else:
        return HttpResponse("Unsupported object type")

    return render(request, template, context=context)
