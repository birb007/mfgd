from enum import IntEnum
from datetime import datetime

from mfgd_app import utils

import pygit2


class ObjectType(IntEnum):
    COMMIT = 1
    TREE = 2
    BLOB = 3


class TreeEntry:
    def __init__(self, entry, last_change, path):
        self.entry = entry
        self.name = entry.name
        self.type = ObjectType(entry.type)
        self.last_change = last_change
        self.path = utils.normalize_path(path)

        if last_change is not None:
            modification_timestamp = datetime.utcfromtimestamp(last_change.commit_time)
            self.change_time = modification_timestamp.strftime("%Y-%m-%d")
            # we have to introduce this field  because django templates do not
            # allow for chained resolution operator calls.
            self.last_change_id = last_change.id
        else:
            self.change_time = ""

        if entry.type == ObjectType.BLOB:
            self.is_binary = entry.is_binary


class FileChange:
    def __init__(self, patch, status_char, status, path, new_blob, old_blob):
        self.status = status_char
        self.deleted = status == pygit2.GIT_DELTA_DELETED
        self.path = path

        self.patch = patch.text
        _, insert, delete = patch.line_stats
        self.insertion = f"++{insert}"
        self.deletion = f"--{delete}"
