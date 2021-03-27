import binascii
import re

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django import urls
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import mpygit

from mfgd_app import utils
from mfgd_app.models import Repository, CanAccess
from mfgd_app.forms import UserForm


def default_branch(db_repo_obj):
    # NOTE: someone please fix this if you can, but the pygit2 API does not
    # provide access to the global HEAD as it's not a proper ref
    with open(db_repo_obj.path + "/.git/HEAD") as f:
        return f.read().split("/")[-1]


def index(request):
    context_dict = {}
    repo_list = Repository.objects.all()
    can_access = CanAccess.objects.all()
    for i, db_repo_obj in enumerate(repo_list):
        # We need to stick the default branch name to each repo here
        repo_list[i].default_branch = default_branch(db_repo_obj)
    context_dict["repositories"] = repo_list
    context_dict["canaccess"] = can_access
    return render(request, "index.html", context_dict)


def read_blob(blob):
    # 100K
    MAX_BLOB_SIZE = 100 * 5 << 10

    content = blob.data
    if blob.is_binary:
        if blob.size > MAX_BLOB_SIZE:
            return "blob_binary.html", None
        return "blob_binary.html", utils.hex_dump(content)
    else:
        if blob.size > MAX_BLOB_SIZE:
            return "blob.html", None
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
        relative_path = "/".join(parts[: off + 1]) + "/"
        url = urls.reverse(
            "view", kwargs={"repo_name": repo_name, "oid": oid, "path": relative_path}
        )
        crumbs.append(Crumb(parts[off], url))
    return crumbs

def gen_branches(repo_name, repo, oid):
    class Branch:
        def __init__(self, name, url):
            self.name = name
            self.url = url

    l = list(repo.heads)
    if oid not in l:
        l.append(oid)

    return [Branch(name, f"/{repo_name}/view/" + name) for name in l]


def view(request, repo_name, oid, path):
    # Find the repo object in the db
    db_repo_obj = Repository.objects.get(name=repo_name)
    # Open a repo object to the requested repo
    repo = mpygit.Repository(db_repo_obj.path)
    # First we normalize the path so libgit2 doesn't choke
    path = utils.normalize_path(path)

    # Find commit in the repo
    commit = utils.find_branch_or_commit(repo, oid)
    if commit is None or not isinstance(commit, mpygit.Commit):
        return HttpResponse("Invalid commit ID")

    # Resolve path inside commit
    obj = utils.resolve_path(repo, commit.tree, path)
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
    if isinstance(obj, mpygit.Tree):
        template = "tree.html"
        context["entries"] = utils.tree_entries(repo, commit, path, obj)
    elif isinstance(obj, mpygit.Blob):
        template, code = read_blob(obj)
        if template == "blob.html":
            context["code"] = utils.highlight_code(path, code)
        else:
            context["code"] = code
        commit = utils.get_file_history(repo, commit, path)
        context["change"] = commit
    else:
        return HttpResponse("Unsupported object type")

    return render(request, template, context=context)


def user_login(request):
    if request.method == "POST":

        # Get the form details and check if they match the data in the database
        username = request.POST.get("username")
        password = request.POST.get("password")

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
        return render(request, "login.html")


def user_register(request):
    registered = False
    # Check if form is valid, if it is, save data to database
    if request.method == 'POST':
        user_form = UserForm(request.POST)

        if user_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            registered = True

        else:
            print(user_form.errors)

    else:
        user_form = UserForm()

    return render(request, 'register.html', context={'user_form': user_form, 'registered': registered})

@login_required
def user_logout(request):
    logout(request)
    return redirect("index")


def info(request, repo_name, oid):
    class FileChange:
        def __init__(self, path, patch, status):
            self.path = path
            self.patch = utils.highlight_code("name.diff", patch)
            self.status = status
            self.deleted = status == "D"

            # The line stats are not very elegant but difflib is kind of limited
            insert = len(re.findall(r"^\+", patch, re.MULTILINE)) - 1
            delete = len(re.findall(r"^-", patch, re.MULTILINE)) - 1
            self.insertion = f"++{insert}"
            self.deletion = f"--{delete}"

    db_repo_obj = Repository.objects.get(name=repo_name)
    repo = mpygit.Repository(db_repo_obj.path)

    commit = utils.find_branch_or_commit(repo, oid)
    if commit is None or not isinstance(commit, mpygit.Commit):
        return HttpResponse("Invalid branch or commit ID")

    changes = []
    parent = repo[commit.parents[0]] if len(commit.parents) > 0 else None
    diffs = utils.diff_commits(repo, parent, commit)
    for path, patch, status in diffs:
        changes.append(FileChange(path, patch, status))

    context = {
        "repo_name": repo_name,
        "oid": oid,
        "commit": commit,
        "changes": changes,
    }

    return render(request, "commit.html", context=context)


def chain(request, repo_name, oid):
    db_repo_obj = Repository.objects.get(name=repo_name)
    # Open a repo object to the requested repo
    repo = mpygit.Repository(db_repo_obj.path)

    obj = utils.find_branch_or_commit(repo, oid)
    if obj is None:
        return HttpResponse("Invalid branch or commit ID")

    context = {
        "repo_name": repo_name,
        "oid": oid,
        "commits": utils.walk(repo, obj.oid)
    }
    return render(request, "chain.html", context=context)


def error_404(request, exception):
    return render(request, "404.html", {})


def error_500(request):
    return render(request, "500.html", {})
