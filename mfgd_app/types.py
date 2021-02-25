from enum import IntEnum
from datetime import datetime

class ObjectType(IntEnum):
    COMMIT = 1
    TREE = 2
    BLOB = 3


class StaticEntry:
    def __init__(self, name, type, last_change):
        self.name = name
        self.type = ObjectType(type)
        self.last_change = last_change

        if last_change is not None:
            modification_timestamp = datetime.utcfromtimestamp(last_change.commit_time)
            self.change_time = modification_timestamp.strftime("%Y-%m-%d")
        else:
            self.change_time = ""
