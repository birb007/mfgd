import binascii
import datetime as dt

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django import urls
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pygit2

from mfgd_app import utils
from mfgd_app.types import ObjectType, TreeEntry, FileChange
from mfgd_app.models import Repository

def default_branch(db_repo_obj):
    # NOTE: someone please fix this if you can, but the pygit2 API does not
    # provide access to the global HEAD as it's not a proper ref
    with open(db_repo_obj.path + "/.git/HEAD") as f:
        return f.read().split("/")[-1]



def index(request):
    context_dict = {}
    repo_list = Repository.objects.all()
    for i, db_repo_obj in enumerate(repo_list):
        # We need to stick the default branch name to each repo here
        repo_list[i].default_branch = default_branch(db_repo_obj)
        # Only select the first 30 chacters in case of overflow
        repo_list[i].description = repo_list[i].description[0:30]
    # Load the repos data here
    context_dict['repositories'] = repo_list
    return render(request, 'index.html', context_dict)


def read_blob(blob):
    # 100K
    MAX_BLOB_SIZE = 100 * 1 << 10

    content = blob.data
    if blob.is_binary:
        if blob.size > MAX_BLOB_SIZE:
            return "blob_binary.html", ""
        return "blob_binary.html", utils.hex_dump(content)
    else:
        if blob.size > MAX_BLOB_SIZE:
            return "blob.html", ""
    return "blob.html", content.decode()


def gen_crumbs(repo_name, oid, path):
    class Crumb:
        def __init__(self, name, url):
            self.name = name
            self.url = url

        def __str__(self):
            return self.name

    crumbs = []
    parts = utils.split_path(path)
    for off in range(len(parts)):
        relative_path = "/".join(parts[:off + 1]) + "/"
        url = urls.reverse("view",
                kwargs={ "repo_name": repo_name,
                         "oid": oid,
                         "path": relative_path })
        crumbs.append(Crumb(parts[off], url))
    return crumbs

def gen_branches(repo_name, repo, oid):
    class Branch:
        def __init__(self, name, url):
            self.name = name
            self.url = url

    l = list(repo.branches.local)
    if oid not in l:
        l.append(oid)

    return [ Branch(name, f"/{repo_name}/view/" + name) for name in l ]

def view(request, repo_name, oid, path):
    # Find the repo object in the db
    db_repo_obj = Repository.objects.get(name=repo_name)
    # Open a pygit2 repo object to the requested repo
    repo = pygit2.Repository(db_repo_obj.path)
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

    context = {
                "repo_name": repo_name,
                "oid": oid,
                "path": path,
                "branches": gen_branches(repo_name, repo, oid),
                "crumbs": gen_crumbs(repo_name, oid, path),
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


def user_login(request):
    if request.method == 'POST':

        # Get the form details and check if they match the data in the database
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return redirect("index")
            else:
                # User account is deactivated
                return HttpResponse("Your account is disabled.")

        else:
            # User account details were incorrect
            print(f"Invalid login details: {username}, {password}")
            return HttpResponse("Invalid login details supplied.")

    else:
        return render(request, 'login.html')


@login_required
def user_logout(request):
    logout(request)
    return redirect("index")


def info(request, repo_name, oid):
    db_repo_obj = Repository.objects.get(name=repo_name)
    # Open a pygit2 repo object to the requested repo
    repo = pygit2.Repository(db_repo_obj.path)

    obj = utils.find_branch_or_commit(repo, oid)
    if obj is None:
        return HttpResponse("Invalid branch or commit ID")
    elif isinstance(obj, pygit2.Branch):
        commit = repo.get(pygti2.Branch.target)
    else:
        commit = obj

    changes = []
    timestamp = dt.datetime.utcfromtimestamp(commit.commit_time).strftime(
            "%Y-%m-%d %H:%M:%S")
    message_subject, message_body = commit.message.split("\n", maxsplit=1)

    # not initial commit
    if len(commit.parents):
        diff = repo.diff(commit.parents[0], commit)
        for delta in diff.deltas:
            new = repo.get(delta.new_file.id)
            old = repo.get(delta.old_file.id)

            status_char = delta.status_char()
            status = delta.status

            diff = utils.get_patch(repo, new, old)
            if old is None:
                path = delta.new_file.path
            else:
                path = delta.old_file.path
            changes.append(FileChange(diff, status_char, status, path, new, old))
    # initial commit
    else:
        for entry in utils.tree_entries(repo, commit, commit.tree, "/"):
            if entry.type != ObjectType.BLOB:
                continue
            patch = utils.get_patch(repo, entry.entry)
            changes.append(
                    FileChange(patch, "A", pygit2.GIT_DELTA_ADDED, entry.path,
                        entry.entry, None))

    context = {
        "repo_name": repo_name,
        "oid": oid,
        "author": commit.author,
        "commit": commit,
        "commit_timestamp": timestamp,
        "changes": changes,
        "message": commit.message,
        "message_subject": message_subject,
        "message_body": message_body,
    }
    return render(request, "commit.html", context=context)
