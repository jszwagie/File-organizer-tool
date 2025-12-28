import os
import hashlib
import stat

class FileEntry:
    def __init__(self, path):
        self.path = path
        self.stat = os.stat(path)
        self.size = self.stat.st_size
        self.mtime = self.stat.st_mtime
        self.mode = stat.S_IMODE(self.stat.st_mode)
        self.name = os.path.basename(path)
        self._hash = None # Lazy loading

    def get_hash(self):
        # Calculate hash only when needed (optimization)
        if self._hash is None:
            # Hashing (MD5 or SHA256)
            hasher = hashlib.md5()
            try:
                with open(self.path, 'rb') as f:
                    buf = f.read(65536)
                    while len(buf) > 0:
                        hasher.update(buf)
                        buf = f.read(65536)
                self._hash = hasher.hexdigest()
            except (IOError, OSError):
                self._hash = None # Handle read errors
        return self._hash

class FileScanner:
    def scan(self, directories):
        files_found = []
        for directory in directories:
            # Resilience to characters in names - os.walk handles it by default
            for root, _, files in os.walk(directory):
                for name in files:
                    full_path = os.path.join(root, name)
                    files_found.append(FileEntry(full_path))
        return files_found