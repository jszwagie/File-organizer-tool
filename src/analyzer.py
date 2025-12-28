import os

class SuggestedAction:
    def __init__(self, file_entry, action_type, reason, target=None):
        self.file_entry = file_entry
        self.action_type = action_type # 'DELETE', 'MOVE', 'RENAME', 'CHMOD', 'SKIP'
        self.reason = reason
        self.target = target # Additional info (e.g., new name, new path, new permissions)

class Analyzer:
    def __init__(self, config):
        self.config = config
        self.suggestions = []

    def _is_in_target(self, file_path, target_root):
        """Check if file is located within the target directory X."""
        return os.path.abspath(file_path).startswith(os.path.abspath(target_root))

    def _get_unique_path(self, target_dir, filename):
        """Generate a unique path in target directory, handling name collisions."""
        base, ext = os.path.splitext(filename)
        new_path = os.path.join(target_dir, filename)
        counter = 1
        while os.path.exists(new_path):
            new_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
            counter += 1
        return new_path

    def analyze(self, files, target_root_x):
        target_root_x = os.path.abspath(target_root_x)
        
        # 1. Garbage Collection - Temporary and empty files
        remaining_files = [] # Files that will proceed to further analysis
        for f in files:
            ext = os.path.splitext(f.name)[1]
            if f.size == 0:
                self.suggestions.append(SuggestedAction(f, 'DELETE', 'Empty file (0 bytes)'))
            elif ext in self.config.temp_exts:
                self.suggestions.append(SuggestedAction(f, 'DELETE', f'Temporary file ({ext})'))
            else:
                remaining_files.append(f)
        
        files = remaining_files

        # 2. Sanitization - Names and attributes
        for f in files:
            # Checking for bad characters in names
            new_name = f.name
            for char in self.config.bad_chars:
                if char in new_name:
                    new_name = new_name.replace(char, self.config.replacement)
            
            if new_name != f.name:
                self.suggestions.append(SuggestedAction(f, 'RENAME', 'Invalid characters in name', new_name))

            # Checking permissions (simplified string comparison)
            current_perms = oct(f.mode)[-3:]
            if current_perms != str(self.config.default_perm):
                self.suggestions.append(SuggestedAction(f, 'CHMOD', f'Unusual attributes ({current_perms})', self.config.default_perm))

        # 3. Deduplication - Group by hash (identical content)
        content_map = {}
        for f in files:
            h = f.get_hash()
            if h:
                content_map.setdefault(h, []).append(f)

        # Track files already handled as duplicates (to exclude from versioning)
        duplicate_paths = set()

        for content_hash, group in content_map.items():
            if len(group) > 1:
                # Found duplicate content
                # Sort: oldest first (keep the oldest as original)
                group.sort(key=lambda x: x.mtime)
                original = group[0]
                duplicates = group[1:]
                
                # Mark all files in this group as handled
                for f in group:
                    duplicate_paths.add(f.path)
                
                # If the original is not in X, suggest moving it to X
                if not self._is_in_target(original.path, target_root_x):
                    new_path = self._get_unique_path(target_root_x, original.name)
                    self.suggestions.append(SuggestedAction(
                        original, 'MOVE', 
                        f'Original file not in target directory',
                        new_path
                    ))

                # Delete duplicates
                for dup in duplicates:
                    self.suggestions.append(SuggestedAction(
                        dup, 'DELETE', 
                        f'Duplicate (original: {original.path})'
                    ))

        # 4. Versioning - Files with same name but different content
        # Group by filename (excluding files already handled as content duplicates)
        name_map = {}
        for f in files:
            if f.path not in duplicate_paths:
                name_map.setdefault(f.name, []).append(f)

        for filename, group in name_map.items():
            if len(group) > 1:
                # Same name, different content (different hashes)
                # Sort: newest first (keep the newer as current version)
                group.sort(key=lambda x: x.mtime, reverse=True)
                newest = group[0]
                older_versions = group[1:]
                
                # Move the newest version to X if not already there
                if not self._is_in_target(newest.path, target_root_x):
                    new_path = os.path.join(target_root_x, newest.name)
                    self.suggestions.append(SuggestedAction(
                        newest, 'MOVE',
                        f'Newest version - move to target directory',
                        new_path
                    ))
                
                # Handle older versions - rename with version suffix or delete
                for i, old_version in enumerate(older_versions):
                    base, ext = os.path.splitext(old_version.name)
                    versioned_name = f"{base}_v{len(older_versions) - i}{ext}"
                    
                    if self._is_in_target(old_version.path, target_root_x):
                        # File is in X - rename it to keep as archived version
                        self.suggestions.append(SuggestedAction(
                            old_version, 'RENAME',
                            f'Older version (conflicts with newer: {newest.path})',
                            versioned_name
                        ))
                    else:
                        # File is in Y - user decides: delete or move with rename
                        new_path = os.path.join(target_root_x, versioned_name)
                        self.suggestions.append(SuggestedAction(
                            old_version, 'MOVE',
                            f'Older version from source directory (newer: {newest.path})',
                            new_path
                        ))
        
        return self.suggestions