import enum
import binascii
import difflib
import re
import string

from mpygit import mpygit, gitutil

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
        entry.last_change = gitutil.get_latest_change(repo, \
                                target.oid, (*split_path(path), entry.name))
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

        if request.user.userprofile.isAdmin:
            permission = permission.CAN_MANAGE
        return endpoint(request, permission, *args, **kwargs)

    return _inner
