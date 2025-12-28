import os

class SuggestedAction:
    def __init__(self, file_entry, action_type, reason, target=None):
        self.file_entry = file_entry
        self.action_type = action_type # 'DELETE', 'MOVE', 'RENAME', 'CHMOD'
        self.reason = reason
        self.target = target # Additional info (e.g., new name, new permissions)

class Analyzer:
    def __init__(self, config):
        self.config = config
        self.suggestions = []

    def analyze(self, files, target_root_x):
        # 1. Temporary and empty files (cite: 15, 21, 23)
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

        # 2. Names and attributes (cite: 24, 25)
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

        # 3. Duplicates (cite: 14) and Versions (cite: 16)
        # Group by hash (identical content)
        content_map = {}
        for f in files:
            h = f.get_hash()
            if h:
                content_map.setdefault(h, []).append(f)

        for content_hash, group in content_map.items():
            if len(group) > 1:
                # Found duplicate content
                # Sort: oldest first (cite: 14 - "keep the oldest")
                group.sort(key=lambda x: x.mtime)
                original = group[0]
                duplicates = group[1:]
                
                # If the original is not in X, suggest moving it to X
                if not original.path.startswith(target_root_x):
                     # Logic to determine new path in X
                     pass 

                for dup in duplicates:
                    self.suggestions.append(SuggestedAction(dup, 'DELETE', f'Duplicate (original: {original.path})'))
        # Logic for files with the same name but different content (cite: 16)
        # (Requires a separate name map, excluding those already classified as content duplicates)
        
        return self.suggestions