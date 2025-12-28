"""
File scanning module.

Provides functionality to recursively scan directories and collect file metadata.
"""

import hashlib
import os
import stat


class FileEntry:
    """Represents a single file with its metadata.
    
    Attributes:
        path: Absolute path to the file.
        name: Filename (basename).
        size: File size in bytes.
        mtime: Modification time (Unix timestamp).
        mode: File permission bits.
    """
    
    def __init__(self, path):
        """Initialize file entry with metadata.
        
        Args:
            path: Path to the file.
            
        Raises:
            OSError: If file cannot be accessed.
        """
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        
        file_stat = os.stat(path)
        self.size = file_stat.st_size
        self.mtime = file_stat.st_mtime
        self.mode = stat.S_IMODE(file_stat.st_mode)
        
        self._hash = None

    def get_hash(self):
        """Calculate MD5 hash of file content (lazy-loaded).
        
        Returns:
            str: Hex digest of file hash, or None if file cannot be read.
        """
        if self._hash is not None:
            return self._hash
            
        hasher = hashlib.md5()
        try:
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            self._hash = hasher.hexdigest()
        except (IOError, OSError):
            self._hash = None
            
        return self._hash

    def __repr__(self):
        return f"FileEntry({self.name!r}, size={self.size}, mode={oct(self.mode)})"


class FileScanner:
    """Recursively scans directories for files.
    
    Attributes:
        follow_symlinks: Whether to follow symbolic links.
        errors: List of errors encountered during scanning.
    """
    
    def __init__(self, follow_symlinks=False):
        """Initialize scanner.
        
        Args:
            follow_symlinks: If True, follow symbolic links (default: False).
        """
        self.follow_symlinks = follow_symlinks
        self.errors = []

    def scan(self, directories):
        """Scan directories recursively for files.
        
        Args:
            directories: List of directory paths to scan.
            
        Returns:
            list[FileEntry]: List of file entries found.
        """
        files_found = []
        seen_paths = set()
        
        for directory in directories:
            self._scan_directory(directory, files_found, seen_paths)
                        
        return files_found

    def _scan_directory(self, directory, files_found, seen_paths):
        """Scan a single directory tree.
        
        Args:
            directory: Directory path to scan.
            files_found: List to append found files to.
            seen_paths: Set of already processed paths.
        """
        directory = os.path.abspath(directory)
        
        if not os.path.isdir(directory):
            self.errors.append(f"Not a directory: {directory}")
            return
            
        for root, _, files in os.walk(directory, followlinks=self.follow_symlinks):
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
        """Get list of errors encountered during scanning.
        
        Returns:
            list[str]: Error messages.
        """
        return self.errors
