from enum import IntEnum
from datetime import datetime

from mfgd_app import utils

import mpygit

class FileChange:
    def __init__(self, patch, status_char, status, path, new_blob, old_blob):
        self.status = status_char
        self.deleted = status == pygit2.GIT_DELTA_DELETED
        self.path = path

        self.patch = patch.text
        _, insert, delete = patch.line_stats
        self.insertion = f"++{insert}"
        self.deletion = f"--{delete}"
