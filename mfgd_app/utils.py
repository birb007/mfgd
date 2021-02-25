import binascii
import re
import string

from mfgd_app.types import ObjectType

# Pre-compiled regex for speed
split_path_re = re.compile(r"/?([^/]+)/?")

def split_path(path):
    """Robust, regex-based, path splitter
    """
    return split_path_re.findall(path)

def normalize_path(path):
    """Normalize user-provided path
    """
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
    for old_commit in repo.walk(commit):
        diff = repo.diff(commit, old_commit)
        for delta in diff.deltas:
            if delta.new_file.path == path:
                return old_commit
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
