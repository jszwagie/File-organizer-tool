"""
File analysis module.

Analyzes scanned files and generates suggested actions for organization.
"""

import os
from enum import Enum, auto


class ActionType(Enum):
    """Types of actions that can be performed on files."""

    DELETE = "DELETE"
    MOVE = "MOVE"
    COPY = "COPY"
    RENAME = "RENAME"
    CHMOD = "CHMOD"
    SKIP = "SKIP"


class AnalysisMode(Enum):
    """Analysis modes for selective file processing."""

    SANITIZATION = auto()  # RENAME (bad chars) + CHMOD (permissions)
    GARBAGE = auto()  # DELETE empty and temp files
    DEDUPLICATION = auto()  # DELETE duplicates, MOVE originals
    CONSOLIDATION = auto()  # MOVE unique files from Y to X
    ALL = auto()  # All of the above


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

    Supports selective analysis modes:
    - SANITIZATION: Fix bad characters in names and normalize permissions
    - GARBAGE: Remove empty and temporary files
    - DEDUPLICATION: Remove duplicate files, handle versioning
    - CONSOLIDATION: Move unique files from source dirs to target
    - ALL: Run all analysis phases
    """

    def __init__(self, config):
        """Initialize analyzer with configuration.

        Args:
            config: AppConfig object with settings.
        """
        self.config = config

    def analyze(self, files, target_dir, mode=AnalysisMode.ALL):
        """Analyze files and generate suggested actions.

        Args:
            files: List of FileEntry objects to analyze.
            target_dir: Target directory path for consolidation.
            mode: AnalysisMode enum specifying which analysis to perform.

        Returns:
            list[SuggestedAction]: List of suggested actions.
        """
        self._target_dir = os.path.abspath(target_dir)
        self._suggestions = []

        if mode == AnalysisMode.SANITIZATION:
            self._analyze_sanitization(files)

        elif mode == AnalysisMode.GARBAGE:
            self._analyze_garbage(files)

        elif mode == AnalysisMode.DEDUPLICATION:
            # Filter out garbage files first (don't process them)
            clean_files = self._filter_garbage(files)
            duplicate_paths = self._analyze_duplicates(clean_files)
            self._analyze_versions(clean_files, duplicate_paths)

        elif mode == AnalysisMode.CONSOLIDATION:
            # Filter garbage, find what's already handled
            clean_files = self._filter_garbage(files)
            duplicate_paths = self._find_duplicate_paths(clean_files)
            version_paths = self._find_version_paths(clean_files, duplicate_paths)
            all_handled = duplicate_paths | version_paths
            self._analyze_consolidation(clean_files, all_handled)

        elif mode == AnalysisMode.ALL:
            # Original behavior - all phases
            files = self._analyze_garbage(files)
            self._analyze_sanitization(files)
            duplicate_paths = self._analyze_duplicates(files)
            handled_paths = self._analyze_versions(files, duplicate_paths)
            all_handled = duplicate_paths | handled_paths
            self._analyze_consolidation(files, all_handled)

        return self._suggestions

    def _filter_garbage(self, files):
        """Filter out empty and temporary files without generating suggestions.

        Args:
            files: List of FileEntry objects.

        Returns:
            list[FileEntry]: Files that are not garbage.
        """
        return [f for f in files if f.size > 0 and not self._is_temp_file(f.name)]

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
            # Check filename for bad characters
            sanitized_name = self._sanitize_filename(f.name)
            if sanitized_name != f.name:
                self._add_suggestion(
                    f, ActionType.RENAME, "Invalid characters in name", sanitized_name
                )

            # Check permissions
            current_perm = oct(f.mode)[-3:]
            if current_perm != self.config.default_perm:
                self._add_suggestion(
                    f,
                    ActionType.CHMOD,
                    f"Non-standard permissions ({current_perm})",
                    self.config.default_perm,
                )

    def _find_duplicate_paths(self, files):
        """Find paths of files that are duplicates (without generating suggestions).

        Args:
            files: List of FileEntry objects.

        Returns:
            set[str]: Paths of duplicate files.
        """
        by_hash = {}
        for f in files:
            h = f.get_hash()
            if h:
                by_hash.setdefault(h, []).append(f)

        duplicate_paths = set()
        for group in by_hash.values():
            if len(group) >= 2:
                duplicate_paths.update(f.path for f in group)

        return duplicate_paths

    def _analyze_duplicates(self, files):
        """Find files with identical content and suggest deduplication.

        Args:
            files: List of FileEntry objects.

        Returns:
            set[str]: Paths of files handled as duplicates.
        """
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

            # Only mark duplicates as handled (original goes to consolidation)
            duplicate_paths.update(f.path for f in duplicates)

            # Delete duplicates (original will be moved in consolidation phase)
            for dup in duplicates:
                self._add_suggestion(
                    dup, ActionType.DELETE, f"Duplicate of {original.path}"
                )

        return duplicate_paths

    def _find_version_paths(self, files, exclude_paths):
        """Find paths of files with version conflicts (without generating suggestions).

        Args:
            files: List of FileEntry objects.
            exclude_paths: Set of paths to exclude.

        Returns:
            set[str]: Paths of files with version conflicts.
        """
        by_name = {}
        for f in files:
            if f.path not in exclude_paths:
                by_name.setdefault(f.name, []).append(f)

        version_paths = set()
        for group in by_name.values():
            if len(group) >= 2:
                version_paths.update(f.path for f in group)

        return version_paths

    def _analyze_versions(self, files, exclude_paths):
        """Handle files with same name but different content.

        Args:
            files: List of FileEntry objects.
            exclude_paths: Set of paths to exclude (already handled).

        Returns:
            set[str]: Paths of files handled in versioning.
        """
        handled_paths = set()

        by_name = {}
        for f in files:
            if f.path not in exclude_paths:
                by_name.setdefault(f.name, []).append(f)

        for filename, group in by_name.items():
            if len(group) < 2:
                continue

            # Keep newest as current version
            group.sort(key=lambda x: x.mtime, reverse=True)
            newest, *older = group

            # Only mark older versions as handled (newest goes to consolidation)
            handled_paths.update(f.path for f in older)

            # Delete all older versions (newest will be moved in consolidation phase)
            for old in older:
                self._add_suggestion(
                    old,
                    ActionType.DELETE,
                    f"Older version (keeping newest: {newest.path})",
                )

        return handled_paths

    def _analyze_consolidation(self, files, exclude_paths):
        """Consolidate unique files from source directories to target.

        Args:
            files: List of FileEntry objects.
            exclude_paths: Set of paths already handled.
        """
        for f in files:
            if f.path in exclude_paths:
                continue

            if not self._is_in_target(f.path):
                new_path = self._unique_path(f.name)
                self._add_suggestion(
                    f,
                    ActionType.MOVE,
                    "Unique file in source - consolidate to target",
                    new_path,
                )

    # Helper methods

    def _add_suggestion(self, file_entry, action_type, reason, target=None):
        """Add a suggestion to the list."""
        self._suggestions.append(
            SuggestedAction(file_entry, action_type, reason, target)
        )

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
