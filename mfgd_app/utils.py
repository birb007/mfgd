import binascii
import re
import string

import mpygit

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

from django.utils.html import escape

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

def walk(repo, oid, max_results=100):
    """Return max_result commits in the history starting from oid
    """
    history = []
    parents = [ oid ]

    while len(parents) > 0 and len(history) <= max_results:
        cur = repo[parents.pop(0)]
        if cur in history:
            # Avoid duplicates by ignoring commits already added
            continue
        history.append(cur)
        parents += cur.parents

    return sorted(history, reverse=True)


def get_file_history(repo, commit, path):
    return commit
    path = path.lstrip("/")

    if isinstance(commit, pygit2.Commit):
        commit = commit.id
    parent = commit

    for commit in repo.walk(commit):
        diff = repo.diff(commit, parent)
        for delta in diff.deltas:
            if delta.new_file.path == path:
                return parent
        parent = commit
    return None


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


def tree_entries(repo, target, tree):
    clean_entries = []
    for entry in tree:
        entry.last_change = target
        if not entry.isdir() and not entry.issubmod():
            blob = repo[entry.oid]
            entry.is_binary = blob.is_binary
        clean_entries.append(entry)

    # secondary sort by name
    clean_entries.sort(key=lambda entry: entry.name)
    # primary sort by type
    clean_entries.sort(key=lambda entry: entry.isdir(), reverse=True)
    return clean_entries


def get_patch(repo, new=None, old=None):
    if old is None:
        id = repo.create_blob("")
        old = repo[id]
        return old.diff(new)
    if new is None:
        return old.diff()
    return old.diff(new)

def highlight_code(filename, code):
    if code is None:
        return None

    try:
        lexer = get_lexer_for_filename(filename, stripall=True)
    except:
        lexer = get_lexer_for_filename("name.txt", stripall=True)
    formatter = HtmlFormatter(linenos=True)
    return highlight(code, lexer, formatter)
