"""
File scanning module.

Provides functionality to recursively scan directories
and collect file metadata.
"""

import hashlib
import os
import stat


class FileEntry:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)

        file_stat = os.stat(path)
        self.size = file_stat.st_size
        self.mtime = file_stat.st_mtime
        self.mode = stat.S_IMODE(file_stat.st_mode)

        self._hash = None

    def get_hash(self):
        if self._hash is not None:
            return self._hash

        hasher = hashlib.md5()
        try:
            with open(self.path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            self._hash = hasher.hexdigest()
        except (IOError, OSError):
            self._hash = None

        return self._hash

    def __repr__(self):
        return f"FileEntry({self.name!r}, size={self.size}, " \
               f"mode={oct(self.mode)})"


class FileScanner:
    def __init__(self, follow_symlinks=False):
        self.follow_symlinks = follow_symlinks
        self.errors = []

    def scan(self, directories):
        files_found = []
        seen_paths = set()

        for directory in directories:
            self._scan_directory(directory, files_found, seen_paths)

        return files_found

    def _scan_directory(self, directory, files_found, seen_paths):
        directory = os.path.abspath(directory)

        if not os.path.isdir(directory):
            self.errors.append(f"Not a directory: {directory}")
            return

        for root, _, files in os.walk(directory,
                                      followlinks=self.follow_symlinks):
            for name in files:
                full_path = os.path.join(root, name)
                abs_path = os.path.abspath(full_path)

                if abs_path in seen_paths:
                    continue
                seen_paths.add(abs_path)

                if os.path.islink(full_path) and not self.follow_symlinks:
                    continue

                if not os.path.isfile(full_path):
                    continue

                try:
                    files_found.append(FileEntry(full_path))
                except (OSError, PermissionError) as e:
                    self.errors.append(f"Cannot access {full_path}: {e}")

    def get_errors(self):
        return self.errors
