"""
File analysis module.

Analyzes scanned files and generates suggested actions for organization.
"""

import os
from enum import Enum


class ActionType(Enum):
    """Types of actions that can be performed on files."""
    DELETE = "DELETE"
    MOVE = "MOVE"
    COPY = "COPY"
    RENAME = "RENAME"
    CHMOD = "CHMOD"
    SKIP = "SKIP"


class SuggestedAction:
    """Represents a suggested action for a file.
    
    Attributes:
        file_entry: The FileEntry this action applies to.
        action_type: Type of action (ActionType enum).
        reason: Human-readable explanation for the action.
        target: Action-specific data (new name, path, or permissions).
    """
    
    def __init__(self, file_entry, action_type, reason, target=None):
        """Initialize suggested action.
        
        Args:
            file_entry: FileEntry object.
            action_type: ActionType enum value.
            reason: Description of why this action is suggested.
            target: Optional target value (new name/path/permissions).
        """
        self.file_entry = file_entry
        self.action_type = action_type
        self.reason = reason
        self.target = target


class Analyzer:
    """Analyzes files and generates organization suggestions.
    
    Performs five types of analysis:
    1. Garbage collection (empty/temporary files)
    2. Sanitization (bad characters, permissions)
    3. Deduplication (identical content)
    4. Versioning (same name, different content)
    5. Consolidation (unique files from Y directories to X)
    """
    
    def __init__(self, config):
        """Initialize analyzer with configuration.
        
        Args:
            config: AppConfig object with settings.
        """
        self.config = config

    def analyze(self, files, target_dir):
        """Analyze files and generate suggested actions.
        
        Args:
            files: List of FileEntry objects to analyze.
            target_dir: Target directory path for consolidation.
            
        Returns:
            list[SuggestedAction]: List of suggested actions.
        """
        self._target_dir = os.path.abspath(target_dir)
        self._suggestions = []
        
        # Phase 1: Remove garbage files from analysis
        files = self._analyze_garbage(files)
        
        # Phase 2: Check sanitization issues
        self._analyze_sanitization(files)
        
        # Phase 3: Find and handle duplicates
        duplicate_paths = self._analyze_duplicates(files)
        
        # Phase 4: Handle version conflicts (excluding duplicates)
        handled_paths = self._analyze_versions(files, duplicate_paths)
        
        # Phase 5: Consolidate unique files from Y to X
        all_handled = duplicate_paths | handled_paths
        self._analyze_consolidation(files, all_handled)
        
        return self._suggestions

    def _analyze_garbage(self, files):
        """Identify empty and temporary files.
        
        Args:
            files: List of FileEntry objects.
            
        Returns:
            list[FileEntry]: Files that passed garbage check.
        """
        remaining = []
        
        for f in files:
            if f.size == 0:
                self._add_suggestion(f, ActionType.DELETE, "Empty file (0 bytes)")
            elif self._is_temp_file(f.name):
                ext = os.path.splitext(f.name)[1]
                self._add_suggestion(f, ActionType.DELETE, f"Temporary file ({ext})")
            else:
                remaining.append(f)
                
        return remaining

    def _analyze_sanitization(self, files):
        """Check for bad characters and incorrect permissions.
        
        Args:
            files: List of FileEntry objects.
        """
        for f in files:
            # Check filename
            sanitized_name = self._sanitize_filename(f.name)
            if sanitized_name != f.name:
                self._add_suggestion(f, ActionType.RENAME, 
                                     "Invalid characters in name", sanitized_name)
            
            # Check permissions
            current_perm = oct(f.mode)[-3:]
            if current_perm != self.config.default_perm:
                self._add_suggestion(f, ActionType.CHMOD,
                                     f"Non-standard permissions ({current_perm})",
                                     self.config.default_perm)

    def _analyze_duplicates(self, files):
        """Find files with identical content and suggest deduplication.
        
        Args:
            files: List of FileEntry objects.
            
        Returns:
            set[str]: Paths of files handled as duplicates.
        """
        # Group by content hash
        by_hash = {}
        for f in files:
            h = f.get_hash()
            if h:
                by_hash.setdefault(h, []).append(f)
        
        duplicate_paths = set()
        
        for group in by_hash.values():
            if len(group) < 2:
                continue
                
            # Keep oldest file as original
            group.sort(key=lambda x: x.mtime)
            original, *duplicates = group
            
            # Mark all as handled
            duplicate_paths.update(f.path for f in group)
            
            # Move original to target if needed
            if not self._is_in_target(original.path):
                new_path = self._unique_path(original.name)
                self._add_suggestion(original, ActionType.MOVE,
                                     "Original not in target directory", new_path)
            
            # Delete duplicates
            for dup in duplicates:
                self._add_suggestion(dup, ActionType.DELETE,
                                     f"Duplicate of {original.path}")
        
        return duplicate_paths

    def _analyze_versions(self, files, exclude_paths):
        """Handle files with same name but different content.
        
        Args:
            files: List of FileEntry objects.
            exclude_paths: Set of paths to exclude (already handled).
            
        Returns:
            set[str]: Paths of files handled in versioning.
        """
        handled_paths = set()
        
        # Group by filename
        by_name = {}
        for f in files:
            if f.path not in exclude_paths:
                by_name.setdefault(f.name, []).append(f)
        
        for filename, group in by_name.items():
            if len(group) < 2:
                continue
            
            # Mark all as handled
            handled_paths.update(f.path for f in group)
            
            # Keep newest as current version
            group.sort(key=lambda x: x.mtime, reverse=True)
            newest, *older = group
            
            # Move newest to target if needed
            if not self._is_in_target(newest.path):
                new_path = os.path.join(self._target_dir, newest.name)
                self._add_suggestion(newest, ActionType.MOVE,
                                     "Current version - consolidate to target", new_path)
            
            # Handle older versions
            for i, old in enumerate(older, start=1):
                version_name = self._versioned_name(old.name, len(older) - i + 1)
                
                if self._is_in_target(old.path):
                    self._add_suggestion(old, ActionType.RENAME,
                                         f"Older version (current: {newest.path})",
                                         version_name)
                else:
                    new_path = os.path.join(self._target_dir, version_name)
                    self._add_suggestion(old, ActionType.MOVE,
                                         f"Older version (current: {newest.path})",
                                         new_path)
        
        return handled_paths

    def _analyze_consolidation(self, files, exclude_paths):
        """Consolidate unique files from source directories to target.
        
        Files that exist only in Y directories and haven't been handled
        by other phases should be moved/copied to X.
        
        Args:
            files: List of FileEntry objects.
            exclude_paths: Set of paths already handled.
        """
        for f in files:
            if f.path in exclude_paths:
                continue
            
            # File not yet handled - check if it's in a source directory
            if not self._is_in_target(f.path):
                new_path = self._unique_path(f.name)
                self._add_suggestion(f, ActionType.MOVE,
                                     "Unique file in source - consolidate to target",
                                     new_path)

    # Helper methods
    
    def _add_suggestion(self, file_entry, action_type, reason, target=None):
        """Add a suggestion to the list."""
        self._suggestions.append(SuggestedAction(file_entry, action_type, reason, target))

    def _is_in_target(self, path):
        """Check if path is within target directory."""
        return os.path.abspath(path).startswith(self._target_dir + os.sep)

    def _is_temp_file(self, filename):
        """Check if filename has a temporary extension."""
        ext = os.path.splitext(filename)[1]
        return ext in self.config.temp_exts

    def _sanitize_filename(self, filename):
        """Replace bad characters in filename."""
        result = filename
        for char in self.config.bad_chars:
            result = result.replace(char, self.config.replacement)
        return result

    def _unique_path(self, filename):
        """Generate unique path in target directory."""
        base, ext = os.path.splitext(filename)
        path = os.path.join(self._target_dir, filename)
        counter = 1
        
        while os.path.exists(path):
            path = os.path.join(self._target_dir, f"{base}_{counter}{ext}")
            counter += 1
            
        return path

    def _versioned_name(self, filename, version):
        """Add version suffix to filename."""
        base, ext = os.path.splitext(filename)
        return f"{base}_v{version}{ext}"
