from mfgd_app.types import ObjectType


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


