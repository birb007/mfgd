import enum
import binascii
import difflib
import re
import string

import mpygit

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

from django.utils.html import escape
from mfgd_app.models import Repository, UserProfile, CanAccess

# Pre-compiled regex for speed
split_path_re = re.compile(r"/?([^/]+)/?")


def split_path(path):
    """Robust, regex-based, path splitter"""
    return split_path_re.findall(path)


def normalize_path(path):
    """Normalize user-provided path"""
    return "/".join(split_path(path))


def resolve_path(repo, oid, path):
    # Resolve tree id
    tree = repo[oid]

    # Check for root of tree
    path = path.strip("/")
    if path == "":
        return tree

    for path_entry in path.split("/"):
        if not isinstance(tree, mpygit.Tree):
            return None
        tree_entry = tree[path_entry]
        if tree_entry == None:
            return None
        tree = repo[tree_entry.oid]

    return tree


def diff_commits(repo, commit1, commit2):
    diffs = []

    def added_blob(path, blob):
        if blob.is_binary:
            diffs.append(("/".join(path), "Binary file added", "A"))
        else:
            patch = "".join(
                difflib.unified_diff(
                    [],
                    blob.text.splitlines(keepends=True),
                    "/dev/null",
                    "/".join(["b"] + path),
                )
            )
            diffs.append(("/".join(path), patch, "A"))

    def modified_blob(path, blob1, blob2):
        if blob1.is_binary or blob2.is_binary:
            diffs.append(("/".join(path), "Binary file modified", "M"))
        else:
            patch = "".join(
                difflib.unified_diff(
                    blob1.text.splitlines(keepends=True),
                    blob2.text.splitlines(keepends=True),
                    "/".join(["a"] + path),
                    "/".join(["b"] + path),
                )
            )
            diffs.append(("/".join(path), patch, "M"))

    def deleted_blob(path, blob):
        if blob.is_binary:
            diffs.append(("/".join(path), "Binary file deleted", "D"))
        else:
            patch = "".join(
                difflib.unified_diff(
                    blob.text.splitlines(keepends=True),
                    [],
                    "/".join(["a"] + path),
                    "/dev/null",
                )
            )
            diffs.append(("/".join(path), patch, "D"))

    def added_subtree(path, tree):
        for entry in tree:
            entry_path = path + [entry.name]
            if entry.isreg():
                added_blob(entry_path, repo[entry.oid])
            elif entry.isdir():
                added_subtree(entry_path, repo[entry.oid])

    def deleted_subtree(path, tree):
        for entry in tree:
            entry_path = path + [entry.name]
            if entry.isreg():
                deleted_blob(entry_path, repo[entry.oid])
            elif entry.isdir():
                deleted_subtree(entry_path, repo[entry.oid])

    def diff_subtree(path, tree1, tree2):
        for entry in tree1:  # Look for deleted blobs
            newent = tree2[entry.name]
            entry_path = path + [entry.name]
            if entry.isreg():
                if newent is None or not newent.isreg():
                    deleted_blob(entry_path, repo[entry.oid])
            elif entry.isdir():
                if newent is None or not newent.isdir():
                    deleted_subtree(entry_path, repo[entry.oid])

        for entry in tree2:  # Look for added or modified blobs
            oldent = tree1[entry.name]
            entry_path = path + [entry.name]
            if entry.isreg():
                if oldent is None or not oldent.isreg():
                    added_blob(entry_path, repo[entry.oid])
                elif entry.oid != oldent.oid:
                    modified_blob(entry_path, repo[oldent.oid], repo[entry.oid])
            elif entry.isdir():
                if oldent is None or not oldent.isdir():
                    added_subtree(entry_path, repo[entry.oid])
                elif entry.oid != oldent.oid:
                    diff_subtree(entry_path, repo[oldent.oid], repo[entry.oid])

    if commit1 is None:
        added_subtree([], repo[commit2.tree])
    else:
        diff_subtree([], repo[commit1.tree], repo[commit2.tree])
    return diffs


def walk(repo, oid, max_results=100):
    """Return max_result commits in the history starting from oid"""
    history = []
    parents = [oid]

    while len(parents) > 0 and len(history) <= max_results:
        cur = repo[parents.pop(0)]
        if cur in history:
            # Avoid duplicates by ignoring commits already added
            continue
        history.append(cur)
        parents += cur.parents

    return sorted(history, reverse=True)


def collect_path_oids(repo, tree_id, path):
    path_oids = []
    for path_entry in split_path(path):
        tree_entry = repo[tree_id][path_entry]
        assert tree_entry is not None
        path_oids.append((tree_entry.name, tree_entry.oid))
        tree_id = tree_entry.oid
    return path_oids


def match_oids(repo, tree_id, path_oids):
    for name, oid in path_oids:
        tree = repo[tree_id]
        ent = tree[name]
        if ent is None:
            return False
        if ent.oid == oid:
            return True
        tree_id = ent.oid
    return False


def get_file_history(repo, commit, path, max_dist=100):
    """Get the latest commit that changed the specified path"""
    base_oids = collect_path_oids(repo, commit.tree, path)

    i = 0
    while i < max_dist:
        if len(commit.parents) == 0:
            return commit
        parent = commit.parents[0]
        if not match_oids(repo, repo[parent].tree, base_oids):
            return commit
        commit = repo[parent]
        i += 1
    return commit


def find_branch_or_commit(repo, oid):
    try:
        obj = repo[oid]
        if obj is None or not isinstance(obj, mpygit.Commit):
            raise ValueError()
        return obj
    except ValueError:
        try:
            return repo[repo.heads[oid]]
        except KeyError:
            return None


def hex_dump(binary):
    ALLOWED_CHARS = set(string.ascii_letters + string.digits + string.punctuation)
    N_BYTES_ROW = 16
    N_BYTES_COL = 8
    N_BYTES_CHUNK = 1

    rows = []
    for row_off in range(0, len(binary), N_BYTES_ROW):
        row = binary[row_off : row_off + N_BYTES_ROW]
        chunks = []
        ascii = ""
        for chunk_off in range(0, len(row), N_BYTES_CHUNK):
            chunk = row[chunk_off : chunk_off + N_BYTES_CHUNK]
            for char in map(chr, chunk):
                if char in ALLOWED_CHARS:
                    ascii += char
                else:
                    ascii += "."
            chunks.append(binascii.b2a_hex(chunk).decode())

        cols = []
        for col_off in range(0, len(chunks), N_BYTES_COL):
            cols.append(" ".join(chunks[col_off : col_off + N_BYTES_COL]))

        offset = "{:08x}".format(row_off)
        rows.append((offset, cols, ascii))
    return rows


def tree_entries(repo, target, path, tree):
    clean_entries = []
    for entry in tree:
        entry.last_change = get_file_history(repo, target, path + "/" + entry.name)
        if not entry.isdir() and not entry.issubmod():
            blob = repo[entry.oid]
            entry.is_binary = blob.is_binary
        clean_entries.append(entry)

    # secondary sort by name
    clean_entries.sort(key=lambda entry: entry.name)
    # primary sort by type
    clean_entries.sort(key=lambda entry: entry.isdir(), reverse=True)
    return clean_entries


def highlight_code(filename, code):
    if code is None:
        return None

    try:
        lexer = get_lexer_for_filename(filename, stripall=True)
    except:
        lexer = get_lexer_for_filename("name.txt", stripall=True)
    formatter = HtmlFormatter(linenos=True)
    return highlight(code, lexer, formatter)


class Permission(enum.IntEnum):
    NO_ACCESS = 0
    CAN_VIEW = 1
    CAN_MANAGE = 2

def verify_user_permissions(endpoint):
    def _inner(request, *args, **kwargs):
        try:
            repo_name = kwargs["repo_name"]
        except KeyError:
            return endpoint(request, Permission.CAN_VIEW, *args, **kwargs)

        # check if repository is public or exists
        permission = Permission.CAN_VIEW
        try:
            repo = Repository.objects.get(name=repo_name)
            permission = Permission.CAN_VIEW if repo.isPublic else Permission.NO_ACCESS
        except Repository.DoesNotExist:  # let view handle failure
            return endpoint(request, Permission.CAN_VIEW, *args, **kwargs)

        if request.user.is_anonymous:
            return endpoint(request, permission, *args, **kwargs)

        # check if user has valid permissions
        try:
            access = CanAccess.objects.get(user=request.user.userprofile, repo=repo)
            if access.canManage:
                permission = Permission.CAN_MANAGE
            else:
                permission = Permission.CAN_VIEW
        except (UserProfile.DoesNotExist, CanAccess.DoesNotExist):
            pass
        return endpoint(request, permission, *args, **kwargs)

    return _inner
