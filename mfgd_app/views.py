import binascii

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django import urls
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pygit2

from mfgd_app import utils
from mfgd_app.types import ObjectType, TreeEntry
from mfgd_app.models import Repository

# Directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Repo
repo = pygit2.Repository(BASE_DIR / ".git")

def index(request):
    context_dict = {}
    repo_list = Repository.objects.all()
    for i, rep in enumerate(repo_list):
        repo_list[i].description = repo_list[i].description[0:30] # Only select the first 30 chacters in case of overflow
    context_dict['repositories'] = repo_list # Load the repos data here
    return render(request, 'index.html', context_dict)

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


def gen_crumbs(oid, path):
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
                kwargs={"oid": oid, "path": relative_path})
        crumbs.append(Crumb(parts[off], url))
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
                "crumbs": gen_crumbs(oid, path),
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
