#
# Read only, pure Python git implementation
#
# This is really outside the scope of the WAD2 project, but I decided to write
# a replacement for pygit2 as it was not flexible enough for our requirements
#
# Author: Mate Kukri
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
S_IFDIR = 0o40000  # directory
S_IFMOD = 0o160000 # submodule

class TreeEntry:
    def __init__(self, name, mode, oid):
        self.name = name
        self.mode = mode
        self.oid = oid

    def isdir(self):
        return (self.mode & S_IFMT) == S_IFDIR

    def issubmod(self):
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
            self._entries[name] = \
                TreeEntry(name, int(mode, 8), binascii.hexlify(rest[:20]).decode())
            data = rest[20:]

    def __getitem__(self, key):
        return self._entries.get(key, None)

    def __iter__(self):
        return iter(self._entries.values())

    def __repr__(self):
        return f"Tree{repr(self.entries.values())}"

class CommitStamp:
    def __init__(self, val):
        # Parse commit stamp
        m = re.match(r"([\s\S]*) \<([\s\S]*)\> ([\s\S]*) ([\s\S]*)", val)
        # Make sure the format was correct
        assert m != None
        self.name, self.email, self.timestamp, self.tz = \
            m.group(1), m.group(2), int(m.group(3)), m.group(4)

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
                self.message = "\n".join(lines[i+1:])
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
            # Read entries
            entry_cnt = self.fanout[-1]
            hashes = idxfile.read(entry_cnt * 20)
            idxfile.read(entry_cnt * 4) # skip CRCs
            indices = struct.unpack(f">{entry_cnt}I", idxfile.read(entry_cnt * 4))
            self.entries = {}
            for i in range(0, len(hashes), 20):
                hash_str = binascii.hexlify(hashes[i:i+20]).decode()
                self.entries[hash_str] = indices[i//20]


    def __getitem__(self, oid):
        """Read an ojbect from the pack file"""
        obj_offs = self.entries.get(oid, None)
        if obj_offs == None:
            return None

        def decode_varint(packfile):
            """Decoder for git's custom variable length packer"""
            b = packfile.read(1)[0]
            obj_type = (b & 0x70) >> 4
            obj_size = b & 0xf
            while b & 0x80:
                b = packfile.read(1)[0]
                obj_size <<= 7
                obj_size |= b & 0x7f
            return obj_type, obj_size

        def decompress_stream(stream, defl_size):
            """Decompress zlib data from a stream without knowing the
            compressed size of said data
            """
            CHUNK_SIZE = 1024
            deflator = zlib.decompressobj()
            defl_data = b""
            while len(defl_data) < defl_size:
                chunk = stream.read(CHUNK_SIZE)
                if chunk == None:
                    break
                defl_data += deflator.decompress(chunk)
                defl_data += deflator.flush()
            return defl_data

        with self.packpath.open("rb") as packfile:
            packfile.seek(obj_offs)
            obj_type, obj_size = decode_varint(packfile)

            assert 0 < obj_type < 5 # TODO: add de-deltifier

            obj_data = decompress_stream(packfile, obj_size)
            if obj_type == 1:
                return Commit(oid, obj_data)
            elif obj_type == 2:
                return Tree(oid, obj_data)
            elif obj_type == 3:
                return Blob(oid, obj_data)
            else:
                print("fail")

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
            # Skip empty lines and comments
            if line == "" or line[0] == "#":
                continue

            # Add packed reference if desired
            val, key = line.split(" ", 1)
            if key.startswith(want):
                realkey = key[len(want):]
                # NOTE: packed refs do *not* take precedence over unpacked ones
                if realkey not in tgt_dict:
                    tgt_dict[realkey] = val

    @property
    def tags(self):
        """List of tags"""
        tags = { ref.name : ref.read_text().strip()
                 for ref in (self.path / "refs" / "tags").iterdir() }
        self._read_packed_refs(tags, "refs/tags/")
        return tags

    @property
    def heads(self):
        """List of heads (aka branches)"""
        heads = { ref.name : ref.read_text().strip()
                 for ref in (self.path / "refs" / "heads").iterdir() }
        self._read_packed_refs(heads, "refs/heads/")
        return heads

    @property
    def HEAD(self):
        """Global head"""

        # Please note that this is a symbolic reference so it might contain
        # either an object ID, or a pointer to an actual reference
        sym_ref = (self.path / "HEAD").read_text()

        m = re.match(r"ref:\s*(\S*)", sym_ref)
        if m != None:
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
                if obj != None:
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
