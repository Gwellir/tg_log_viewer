import zlib
from pathlib import Path
from shutil import copy, move

from tg_log_viewer.settings import MEDIA_ROOT


def crc32(filename):
    with open(filename, 'rb') as fh:
        hash = 0
        while True:
            s = fh.read(65536)
            if not s:
                break
            hash = zlib.crc32(s, hash)
        return "%08X" % (hash & 0xFFFFFFFF)


class FileData:
    """Used for converting any repeatable telegram log media entries into local DB
    naming format (like stickers and reaction GIFs)"""

    def __init__(self, old_file: str):
        old_file_path = Path(old_file)
        self._subdir = old_file_path.parent.name
        self._name = old_file_path.stem
        self._ext = old_file_path.suffix
        self.hash = crc32(old_file_path)
        self.size = old_file_path.stat().st_size

    def get_name(self) -> str:
        return f"{self.hash}_{self.size}{self._ext}"

    def get_media_path(self) -> Path:
        return Path(self._subdir) / Path(self.get_name())

    def get_full_path(self) -> Path:
        return MEDIA_ROOT / self._subdir / self.get_name()


def hashify_copy(old_file: str) -> FileData:
    fdata = FileData(old_file)
    new_file = fdata.get_full_path()
    print(new_file)
    if not new_file.exists():
        copy(old_file, new_file)

    return fdata


def hashify_rename(old_file: str) -> FileData:
    fdata = FileData(old_file)
    new_file = fdata.get_full_path()
    print(new_file)
    if not new_file.exists():
        move(old_file, new_file)

    return fdata
