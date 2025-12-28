"""
Action execution module.

Executes suggested file operations with user confirmation.
"""

import os
import shutil

from .analyzer import ActionType


class ActionExecutor:
    """Executes file operations based on suggested actions.
    
    Supports interactive confirmation with 'always' mode for batch operations.
    """
    
    def __init__(self):
        """Initialize executor with all 'always' flags disabled."""
        self._always = {
            ActionType.DELETE: False,
            ActionType.RENAME: False,
            ActionType.CHMOD: False,
            ActionType.MOVE: False,
        }

    def process_suggestions(self, suggestions):
        """Process list of suggested actions with user interaction.
        
        Args:
            suggestions: List of SuggestedAction objects.
        """
        if not suggestions:
            print("No actions to perform.")
            return

        print(f"\nFound {len(suggestions)} suggested action(s).\n")

        for action in suggestions:
            self._display_action(action)
            
            if self._always.get(action.action_type, False):
                self._execute(action)
                continue
            
            choice = self._get_user_choice()
            
            if choice == 'q':
                print("Quitting...")
                break
            elif choice == 'a':
                self._always[action.action_type] = True
                self._execute(action)
            elif choice == 'y':
                self._execute(action)
            else:
                print("Skipped.")

    def _display_action(self, action):
        """Display action details to user.
        
        Args:
            action: SuggestedAction object.
        """
        print(f"\nFILE: {action.file_entry.path}")
        print(f"ISSUE: {action.reason}")
        
        target_info = f" -> {action.target}" if action.target else ""
        print(f"ACTION: {action.action_type.value}{target_info}")

    def _get_user_choice(self):
        """Get user input for action confirmation.
        
        Returns:
            str: Single character choice ('y', 'n', 'a', or 'q').
        """
        prompt = "Confirm: [y]es, [n]o, [a]lways for this type, [q]uit: "
        return input(prompt).lower().strip()[:1]

    def _execute(self, action):
        """Execute a single action.
        
        Args:
            action: SuggestedAction object.
        """
        handlers = {
            ActionType.DELETE: self._do_delete,
            ActionType.RENAME: self._do_rename,
            ActionType.CHMOD: self._do_chmod,
            ActionType.MOVE: self._do_move,
            ActionType.SKIP: self._do_skip,
        }
        
        handler = handlers.get(action.action_type, self._do_skip)
        
        try:
            handler(action)
        except OSError as e:
            print(f"Error: {e}")

    def _do_delete(self, action):
        """Delete a file."""
        os.remove(action.file_entry.path)
        print("Deleted.")

    def _do_rename(self, action):
        """Rename a file in its current directory."""
        dir_path = os.path.dirname(action.file_entry.path)
        new_path = self._resolve_collision(dir_path, action.target)
        os.rename(action.file_entry.path, new_path)
        print(f"Renamed to: {os.path.basename(new_path)}")

    def _do_chmod(self, action):
        """Change file permissions."""
        mode = int(str(action.target), 8)
        os.chmod(action.file_entry.path, mode)
        print(f"Permissions set to: {action.target}")

    def _do_move(self, action):
        """Move a file to target path."""
        target_dir = os.path.dirname(action.target)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # Handle collision at target
        target_path = action.target
        if os.path.exists(target_path):
            filename = os.path.basename(target_path)
            target_path = self._resolve_collision(target_dir, filename)
        
        shutil.move(action.file_entry.path, target_path)
        print(f"Moved to: {target_path}")

    def _do_skip(self, action):
        """Skip action (no operation)."""
        print("Skipped.")

    def _resolve_collision(self, directory, filename):
        """Generate unique path if file already exists.
        
        Args:
            directory: Target directory path.
            filename: Desired filename.
            
        Returns:
            str: Unique file path.
        """
        path = os.path.join(directory, filename)
        
        if not os.path.exists(path):
            return path
        
        base, ext = os.path.splitext(filename)
        counter = 1
        
        while os.path.exists(path):
            path = os.path.join(directory, f"{base}_{counter}{ext}")
            counter += 1
        
        return path
