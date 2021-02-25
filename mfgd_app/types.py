from enum import IntEnum
from datetime import datetime

class ObjectType(IntEnum):
    COMMIT = 1
    TREE = 2
    BLOB = 3


class TreeEntry:
    def __init__(self, entry, last_change):
        self.name = entry.name
        self.type = ObjectType(entry.type)
        self.last_change = last_change

        if last_change is not None:
            modification_timestamp = datetime.utcfromtimestamp(last_change.commit_time)
            self.change_time = modification_timestamp.strftime("%Y-%m-%d")
        else:
            self.change_time = ""

        if entry.type == ObjectType.BLOB:
            self.is_binary = entry.is_binary
