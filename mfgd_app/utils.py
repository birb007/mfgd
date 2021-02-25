from mfgd_app.types import ObjectType
import re

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

def get_parent(n):
    """Return a path pointing to the nth parent
    """
    return "/".join([ ".." for i in range(n) ])

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


