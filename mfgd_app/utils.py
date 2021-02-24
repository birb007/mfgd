from enum import IntEnum


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


class ObjectType(IntEnum):
    TREE = 2
    BLOB = 3
