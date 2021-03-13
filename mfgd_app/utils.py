import binascii
import re
import string

import pygit2

from mfgd_app.types import ObjectType, TreeEntry

# Pre-compiled regex for speed
split_path_re = re.compile(r"/?([^/]+)/?")


def split_path(path):
    """Robust, regex-based, path splitter"""
    return split_path_re.findall(path)


def normalize_path(path):
    """Normalize user-provided path"""
    return "/".join(split_path(path))


def resolve_path(subtree, path):
    path = path.strip("/")
    if path == "":
        return subtree

    *route, target = path.split("/")
    for directory in route:
        for entry in subtree:
            if entry.name == directory:
                break
        else:
            return None
        subtree = entry

    for entry in subtree:
        if entry.name == target:
            return entry


def get_file_history(repo, commit, path):
    path = path.lstrip("/")

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
        obj = repo.get(oid)
        if obj is None or obj.type != ObjectType.COMMIT:
            raise ValueError()
        return obj
    except ValueError:
        try:
            branch_ref = repo.references[f"refs/heads/{oid}"]
            return repo.get(branch_ref.target)
        except KeyError:
            return None


def hex_dump(binary):
    FMT = "{offset:08x}: {chunks} | {ascii}"
    ALLOWED_CHARS = set(string.ascii_letters + string.digits + string.punctuation + " ")
    N_BYTES_ROW = 32
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

        offset = "{:08x}".format(row_off)
        rows.append((offset, " ".join(chunks), ascii))
    return rows


def tree_entries(repo, target, tree, path):
    clean_entries = []
    for entry in tree:
        # Avoid displaying commit objects which might appear here
        # (such as when browsing a non-default branch)
        if entry.type_str != "blob" and entry.type_str != "tree":
            continue
        entry_path = normalize_path(path) + "/" + entry.name
        change = get_file_history(repo, target.id, entry_path)
        wrapper = TreeEntry(entry, change, entry_path)
        clean_entries.append(wrapper)

    clean_entries.sort(key=lambda entry: entry.name)  # secondary sort by name
    clean_entries.sort(key=lambda entry: entry.type)  # primary sort by type
    return clean_entries


def get_patch(repo, new=None, old=None):
    if old is None:
        id = repo.create_blob("")
        old = repo[id]
        return old.diff(new)
    if new is None:
        return old.diff()
    return new.diff(old)
