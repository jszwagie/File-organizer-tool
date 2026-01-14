"""
File analysis module.

Analyzes scanned files and generates suggested actions for organization.
"""

import os
from enum import Enum, auto


class ActionType(Enum):
    DELETE = "DELETE"
    MOVE = "MOVE"
    COPY = "COPY"
    RENAME = "RENAME"
    CHMOD = "CHMOD"
    SKIP = "SKIP"


class AnalysisMode(Enum):
    SANITIZATION = auto()
    GARBAGE = auto()
    DEDUPLICATION = auto()
    CONSOLIDATION = auto()
    ALL = auto()  # All of the above


class SuggestedAction:
    def __init__(self, file_entry, action_type, reason, target=None):
        self.file_entry = file_entry
        self.action_type = action_type
        self.reason = reason
        self.target = target


class Analyzer:
    def __init__(self, config):
        self.config = config

    def analyze(self, files, target_dir, mode=AnalysisMode.ALL):
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
            version_paths = self._find_version_paths(
                clean_files, duplicate_paths)
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
        return [
            f for f in files
            if f.size > 0 and not self._is_temp_file(f.name)
        ]

    def _analyze_garbage(self, files):
        remaining = []

        for f in files:
            if f.size == 0:
                self._add_suggestion(
                    f, ActionType.DELETE, "Empty file (0 bytes)")
            elif self._is_temp_file(f.name):
                ext = os.path.splitext(f.name)[1]
                self._add_suggestion(
                    f, ActionType.DELETE, f"Temporary file ({ext})")
            else:
                remaining.append(f)

        return remaining

    def _analyze_sanitization(self, files):
        for f in files:
            # Check filename for bad characters
            sanitized_name = self._sanitize_filename(f.name)
            if sanitized_name != f.name:
                self._add_suggestion(
                    f, ActionType.RENAME,
                    "Invalid characters in name", sanitized_name)

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

            duplicate_paths.update(f.path for f in duplicates)
            for dup in duplicates:
                self._add_suggestion(
                    dup, ActionType.DELETE, f"Duplicate of {original.path}"
                )

        return duplicate_paths

    def _find_version_paths(self, files, exclude_paths):
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
        handled_paths = set()

        by_name = {}
        for f in files:
            if f.path not in exclude_paths:
                by_name.setdefault(f.name, []).append(f)

        for filename, group in by_name.items():
            if len(group) < 2:
                continue

            group.sort(key=lambda x: x.mtime, reverse=True)
            newest, *older = group
            handled_paths.update(f.path for f in older)
            for old in older:
                self._add_suggestion(
                    old,
                    ActionType.DELETE,
                    f"Older version (keeping newest: {newest.path})",
                )

        return handled_paths

    def _analyze_consolidation(self, files, exclude_paths):
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

    def _add_suggestion(self, file_entry, action_type, reason, target=None):
        self._suggestions.append(
            SuggestedAction(file_entry, action_type, reason, target)
        )

    def _is_in_target(self, path):
        return os.path.abspath(path).startswith(
            self._target_dir + os.sep)

    def _is_temp_file(self, filename):
        ext = os.path.splitext(filename)[1]
        return ext in self.config.temp_exts

    def _sanitize_filename(self, filename):
        result = filename
        for char in self.config.bad_chars:
            result = result.replace(char, self.config.replacement)
        return result

    def _unique_path(self, filename):
        base, ext = os.path.splitext(filename)
        path = os.path.join(self._target_dir, filename)
        counter = 1

        while os.path.exists(path):
            path = os.path.join(self._target_dir, f"{base}_{counter}{ext}")
            counter += 1

        return path

    def _versioned_name(self, filename, version):
        base, ext = os.path.splitext(filename)
        return f"{base}_v{version}{ext}"
