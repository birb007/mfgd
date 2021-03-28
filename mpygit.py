#
# Read only, pure Python git implementation
#
# This is really outside the scope of the WAD2 project, but I decided to write
# a replacement for pygit2 as it was not flexible enough for our requirements
#
# License for this file:
#
# Copyright (C) Mate Kukri, 2021
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import binascii
import configparser
import pathlib
import re
import struct
import zlib


class Blob:
    def __init__(self, oid, data):
        self.oid = oid
        self.data = data
        self.size = len(data)
        try:
            self.text = data.decode("utf-8")
            self.is_binary = False
        except:
            self.is_binary = True


S_IFMT = 0o170000
S_IFDIR = 0o040000  # directory
S_IFREG = 0o100000  # regular file
S_IFLNK = 0o120000  # symbolic link
S_IFMOD = 0o160000  # submodule


class TreeEntry:
    def __init__(self, name, mode, oid):
        self.name = name
        self.mode = mode
        self.oid = oid

    def isdir(self):
        """Is this entry a directory"""
        return (self.mode & S_IFMT) == S_IFDIR

    def isreg(self):
        """Is this entry a regular file"""
        return (self.mode & S_IFMT) == S_IFREG

    def islnk(self):
        """Is this entry a symbolic link"""
        return (self.mode & S_IFMT) == S_IFLNK

    def issubmod(self):
        """Is entry a submodule"""
        return (self.mode & S_IFMT) == S_IFMOD

    def __repr__(self):
        return f"({self.name} {self.mode:o} {self.oid})"


class Tree:
    def __init__(self, oid, data):
        self.oid = oid
        self._entries = {}

        while len(data) > 0:
            meta, rest = data.split(b"\x00", 1)
            meta = meta.decode()
            mode, name = meta.split(" ", 1)
            self._entries[name] = TreeEntry(
                name, int(mode, 8), binascii.hexlify(rest[:20]).decode()
            )
            data = rest[20:]

    def __getitem__(self, key):
        return self._entries.get(key, None)

    def __iter__(self):
        return iter(self._entries.values())

    def __repr__(self):
        return f"Tree{repr(self._entries.values())}"


class CommitStamp:
    def __init__(self, val):
        # Parse commit stamp
        m = re.match(r"([\s\S]*) \<([\s\S]*)\> ([\s\S]*) ([\s\S]*)", val)
        # Make sure the format was correct
        assert m is not None
        self.name, self.email, self.timestamp, self.tz = (
            m.group(1),
            m.group(2),
            int(m.group(3)),
            m.group(4),
        )

    def __repr__(self):
        return f"{self.name} <{self.email}>"


class Commit:
    def __init__(self, oid, data):
        self.oid = oid

        data_str = data.decode()
        lines = data_str.split("\n")
        if lines[-1] == "":
            lines.pop(-1)

        # Create list for parent commits
        self.parents = []

        # Parse metadata
        for i, line in enumerate(lines):
            if line == "":
                self.message = "\n".join(lines[i + 1 :])
                break

            key, val = line.split(" ", 1)
            if key == "tree":
                self.tree = val
            elif key == "parent":
                self.parents.append(val)
            elif key == "author":
                self.author = CommitStamp(val)
            elif key == "committer":
                self.committer = CommitStamp(val)

    @property
    def short_oid(self):
        return self.oid[:8]

    def __eq__(self, other):
        if other is None:
            return False
        return self.oid == other.oid

    def __lt__(self, other):
        return self.committer.timestamp < other.committer.timestamp

    def __repr__(self):
        return f"{self.author} {self.message}"


class PackFile:
    def __init__(self, idxpath, packpath):
        self.idxpath = pathlib.Path(idxpath)
        self.packpath = pathlib.Path(packpath)

        # Load pack index
        # Please note that for now we only support the v2 idx format
        with self.idxpath.open("rb") as idxfile:
            # Check magic number
            assert idxfile.read(4) == b"\377tOc"
            # Check version number
            assert idxfile.read(4) == b"\x00\x00\x00\x02"
            # Read fan-out table
            self.fanout = struct.unpack(">256I", idxfile.read(256 * 4))

    def _get_offset(self, oid):
        """Resolve an object ID into an offset into the file"""
        oid_bytes = binascii.unhexlify(oid)

        # Find previous fanout entry
        prev_cnt = self.fanout[oid_bytes[0] - 1] if oid_bytes[0] > 0 else 0
        # Count of hashes starting with our first byte
        cnt = self.fanout[oid_bytes[0]] - prev_cnt
        if cnt == 0:
            return None

        # Binary search the index file for our hash
        def hash_offs(idx):
            return 1032 + (prev_cnt + idx) * 20

        def entry_off(idx):
            return 1032 + self.fanout[-1] * 24 + (prev_cnt + idx) * 4

        def bigentry_off(idx):
            return 1032 + self.fanout[-1] * 28 + idx * 8

        def compare_hash(h1, h2):
            idx = 0
            while idx < 20 and h1[idx] == h2[idx]:
                idx += 1
            if idx == 20:
                return 0
            if h1[idx] < h2[idx]:
                return -1
            else:
                return 1

        def bsearch_hash(file):
            left = 0
            right = cnt - 1
            while left <= right:
                mid = (left + right) // 2
                idxfile.seek(hash_offs(mid))
                cur_hash = idxfile.read(20)
                result = compare_hash(cur_hash, oid_bytes)
                if result < 0:
                    left = mid + 1
                elif result > 0:
                    right = mid - 1
                else:
                    return mid
            return None

        with self.idxpath.open("rb") as idxfile:
            entry_idx = bsearch_hash(idxfile)
            if entry_idx is None:
                return None
            idxfile.seek(entry_off(entry_idx))
            (off,) = struct.unpack(">I", idxfile.read(4))
            if off > 0x7fffffff:
                idxfile.seek(bigentry_off(off & 0x7fffffff))
            if off > 0x7FFFFFFF:
                idxfile.seek(bigentry_off(off & 0x7FFFFFFF))
                (off,) = struct.unpack(">Q", idxfile.read(8))

        return off

    def _get_object(self, oid, obj_offs=None):
        """Read the raw underlying data of an object"""
        if obj_offs is None:
            obj_offs = self._get_offset(oid)
            if obj_offs is None:
                return None

        def decode_obj_header(packfile):
            """Decode the variable length object header"""
            b = packfile.read(1)[0]
            obj_type = (b & 0x70) >> 4
            obj_size = b & 0xF
            shift = 4
            while b & 0x80:
                b = packfile.read(1)[0]
                obj_size |= (b & 0x7F) << shift
                shift += 7
            return obj_type, obj_size

        def decompress_stream(stream):
            """Decompress zlib data from a stream without knowing the
            compressed size of said data
            """
            CHUNK_SIZE = 1024
            deflator = zlib.decompressobj()
            defl_data = b""
            while True:
                chunk = stream.read(CHUNK_SIZE)
                if chunk is None:
                    break

                # This is ugly, but as soon as we hit invalid data we break,
                # this is the only way to decompress data without knowing its
                # length using python's zlib library
                try:
                    defl_data += deflator.decompress(chunk)
                    defl_data += deflator.flush()
                except:
                    break
            return defl_data

        def apply_delta(base_data, delta_data):
            """Apply a delta to the provided base data"""

            # Current index into the delta buffer
            idx = 0

            def decode_varint():
                """Decode a variable length integer"""
                nonlocal delta_data
                nonlocal idx
                num = 0
                shift = 0
                while True:
                    b = delta_data[idx]
                    idx += 1
                    num |= (b & 0x7F) << shift
                    shift += 7
                    if (b & 0x80) == 0:
                        break
                return num

            # Read base length and verify it
            base_len = decode_varint()
            assert base_len == len(base_data)

            # Read expected result length
            result_len = decode_varint()

            def decode_copy_delta(mask):
                """Decode a copy delta operand based on the provided mask"""
                nonlocal delta_data
                nonlocal idx
                bit = 1
                num = 0
                shift = 0
                while bit <= mask:
                    if (mask & bit) != 0:
                        num |= delta_data[idx] << shift
                        idx += 1
                    shift += 8
                    bit <<= 1
                return num

            result = b""
            while idx < len(delta_data):
                # Read opcode
                op = delta_data[idx]
                idx += 1
                if op & 0x80 != 0:
                    # Copy from base object
                    offs = decode_copy_delta(op & 0xF)
                    size = decode_copy_delta((op & 0x70) >> 4)
                    assert offs < len(base_data)
                    assert offs + size <= len(base_data)
                    if size == 0:
                        # NOTE: this is a "lovely" undocumented special case I
                        # found out about after banging my head into the table
                        # for 5 hours, than finally deciding to read the sources
                        size = 0x10000
                    result += base_data[offs : offs + size]
                else:
                    # Add from delta data
                    assert op != 0
                    assert idx < len(delta_data)
                    assert idx + op <= len(delta_data)
                    result += delta_data[idx : idx + op]
                    idx += op

            # Verify result length, than return result
            assert result_len == len(result)
            return result

        with self.packpath.open("rb") as packfile:
            packfile.seek(obj_offs)
            obj_type, obj_size = decode_obj_header(packfile)

            # De-deltify object if needed
            if obj_type == 6:
                # Read negative object offset
                # NOTE: this is encoded in a completely unspecified way, that
                # all blogposts get wrong, and the git documentation doesn't
                # mention at all, the real decoding algorithm can be found in
                # "builtin/index-pack.c" in the git source tree
                b = packfile.read(1)[0]
                offset = b & 0x7F
                while (b & 0x80) != 0:
                    offset += 1
                    b = packfile.read(1)[0]
                    offset <<= 7
                    offset |= b & 0x7F
                # Read base object
                base_type, base_data = self._get_object(
                    None, obj_offs=obj_offs - offset
                )
                # Apply deltas
                obj_type = base_type
                delta_data = decompress_stream(packfile)
                assert obj_size == len(delta_data)
                obj_data = apply_delta(base_data, delta_data)
            elif obj_type == 7:
                # Read base object
                base_oid = binascii.hexlify(packfile.read(20)).decode()
                base_type, base_data = self._get_object(base_oid)
                # Apply deltas
                obj_type = base_type
                delta_data = decompress_stream(packfile)
                assert obj_size == len(delta_data)
                obj_data = apply_delta(base_data, delta_data)
            else:
                # Just simple compressed data
                obj_data = decompress_stream(packfile)
                assert obj_size == len(obj_data)

            return obj_type, obj_data

    def __getitem__(self, oid):
        """Read an object from the pack file"""
        obj = self._get_object(oid)
        if obj is None:
            return None
        obj_type, obj_data = obj

        if obj_type == 1:
            return Commit(oid, obj_data)
        elif obj_type == 2:
            return Tree(oid, obj_data)
        elif obj_type == 3:
            return Blob(oid, obj_data)

        return None


class Repository:
    def __init__(self, path):
        # Save repo path
        self.path = pathlib.Path(path)
        # Check for non-bare repo
        if (self.path / ".git").is_dir():
            self.path = self.path / ".git"
        # Read packs
        self.packs = []
        packdir = self.path / "objects" / "pack"
        for idxpath in packdir.glob("*.idx"):
            pack_name = idxpath.name[:-4] + ".pack"
            self.packs.append(PackFile(idxpath, packdir / pack_name))

    @property
    def config(self):
        config = configparser.ConfigParser()
        config.read(self.path / "config")
        return config

    def _read_packed_refs(self, tgt_dict, want):
        packed_refs_path = self.path / "packed-refs"

        # Return if packed references file is empty
        if not packed_refs_path.exists():
            return

        for line in packed_refs_path.read_text().split("\n"):
            # Skip empty lines and comments, and peel lines (we don't care
            # about tags for now)
            if line == "" or line[0] == "#" or line[0] == "^":
                continue

            # Add packed reference if desired
            val, key = line.split(" ", 1)
            if key.startswith(want):
                realkey = key[len(want) :]
                # NOTE: packed refs do *not* take precedence over unpacked ones
                if realkey not in tgt_dict:
                    tgt_dict[realkey] = val

    @property
    def tags(self):
        """List of tags"""
        tags = {
            ref.name: ref.read_text().strip()
            for ref in (self.path / "refs" / "tags").iterdir()
        }
        self._read_packed_refs(tags, "refs/tags/")
        return tags

    @property
    def heads(self):
        """List of heads (aka branches)"""
        heads = {
            ref.name: ref.read_text().strip()
            for ref in (self.path / "refs" / "heads").iterdir()
        }
        self._read_packed_refs(heads, "refs/heads/")
        return heads

    @property
    def HEAD(self):
        """Global head"""

        # Please note that this is a symbolic reference so it might contain
        # either an object ID, or a pointer to an actual reference
        sym_ref = (self.path / "HEAD").read_text()

        m = re.match(r"ref:\s*(\S*)", sym_ref)
        if m is not None:
            return m.group(1)
        else:
            return sym_ref

    def __getitem__(self, oid):
        """Lookup an object ID in the repository"""

        # Expected location on disk
        obj_path = self.path / "objects" / oid[:2] / oid[2:]

        if not obj_path.is_file():
            # Look for object in packs
            for pack in self.packs:
                obj = pack[oid]
                if obj is not None:
                    return obj
        else:
            # Found object on disk
            obj_hdr, obj_data = zlib.decompress(obj_path.read_bytes()).split(b"\x00", 1)
            obj_type, obj_size = obj_hdr.split(b" ")

            if obj_type == b"blob":
                return Blob(oid, obj_data)
            elif obj_type == b"tree":
                return Tree(oid, obj_data)
            elif obj_type == b"commit":
                return Commit(oid, obj_data)

        return None
