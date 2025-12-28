import os
import hashlib
import stat

class FileEntry:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.stat = os.stat(path)  # follows symlinks by default
        self.size = self.stat.st_size
        self.mtime = self.stat.st_mtime
        self.mode = stat.S_IMODE(self.stat.st_mode)
        self.name = os.path.basename(path)
        self._hash = None  # Lazy loading

    def get_hash(self):
        """Calculate hash only when needed (optimization)."""
        if self._hash is None:
            # Hashing using MD5 for speed (sufficient for deduplication)
            hasher = hashlib.md5()
            try:
                with open(self.path, 'rb') as f:
                    buf = f.read(65536)
                    while len(buf) > 0:
                        hasher.update(buf)
                        buf = f.read(65536)
                self._hash = hasher.hexdigest()
            except (IOError, OSError):
                self._hash = None  # Handle read errors
        return self._hash

    def __repr__(self):
        return f"FileEntry({self.name}, size={self.size}, mode={oct(self.mode)})"


class FileScanner:
    def __init__(self, follow_symlinks=False):
        """Initialize scanner with options.
        
        Args:
            follow_symlinks: If False, symlinks are skipped (safer default).
        """
        self.follow_symlinks = follow_symlinks
        self.errors = []  # Collect errors during scanning

    def scan(self, directories):
        """Scan directories recursively and return list of FileEntry objects.
        
        Args:
            directories: List of directory paths to scan.
            
        Returns:
            List of FileEntry objects for all regular files found.
        """
        files_found = []
        seen_paths = set()  # Avoid duplicates from overlapping directories
        
        for directory in directories:
            directory = os.path.abspath(directory)
            if not os.path.isdir(directory):
                self.errors.append(f"Not a directory or doesn't exist: {directory}")
                continue
                
            # os.walk handles special characters in names correctly
            for root, dirs, files in os.walk(directory, followlinks=self.follow_symlinks):
                for name in files:
                    full_path = os.path.join(root, name)
                    abs_path = os.path.abspath(full_path)
                    
                    # Skip if already seen (overlapping directories)
                    if abs_path in seen_paths:
                        continue
                    seen_paths.add(abs_path)
                    
                    # Skip symlinks if not following them
                    if os.path.islink(full_path) and not self.follow_symlinks:
                        continue
                    
                    # Skip if not a regular file
                    if not os.path.isfile(full_path):
                        continue
                    
                    try:
                        files_found.append(FileEntry(full_path))
                    except (OSError, PermissionError) as e:
                        self.errors.append(f"Cannot access {full_path}: {e}")
                        
        return files_found

    def get_errors(self):
        """Return list of errors encountered during scanning."""
        return self.errors