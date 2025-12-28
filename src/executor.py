import os
import shutil

class ActionExecutor:
    def __init__(self):
        # Variables for "always" mode
        self.always_delete = False
        self.always_rename = False
        self.always_chmod = False
        self.always_move = False

    def process_suggestions(self, suggestions):
        if not suggestions:
            print("No actions to perform.")
            return

        for action in suggestions:
            print(f"\nFILE : {action.file_entry.path}")
            print(f"PROBLEM: {action.reason}")
            print(f"SUGGESTION: {action.action_type} -> {action.target if action.target else ''}")

            # If "always" was previously chosen for this type, skip the question
            if self._should_auto_execute(action.action_type):
                self._execute(action)
                continue
            
            choice = input("Choose action: [y]es, [n]o, [a]lways for this type, [q]uit: ").lower().strip()

            if choice == 'q':
                print("Quitting...")
                break
            elif choice == 'a':
                self._set_always(action.action_type)
                self._execute(action)
            elif choice == 'y':
                self._execute(action)
            else:
                print("Skipped.")

    def _should_auto_execute(self, action_type):
        """Check if 'always' mode is enabled for this action type."""
        if action_type == 'DELETE':
            return self.always_delete
        elif action_type == 'RENAME':
            return self.always_rename
        elif action_type == 'CHMOD':
            return self.always_chmod
        elif action_type == 'MOVE':
            return self.always_move
        return False

    def _set_always(self, action_type):
        """Enable 'always' mode for specific action type."""
        if action_type == 'DELETE':
            self.always_delete = True
        elif action_type == 'RENAME':
            self.always_rename = True
        elif action_type == 'CHMOD':
            self.always_chmod = True
        elif action_type == 'MOVE':
            self.always_move = True

    def _execute(self, action):
        try:
            if action.action_type == 'DELETE':
                os.remove(action.file_entry.path)
                print("Deleted.")
            elif action.action_type == 'RENAME':
                dir_name = os.path.dirname(action.file_entry.path)
                new_path = os.path.join(dir_name, action.target)
                # Handle case where target already exists
                if os.path.exists(new_path):
                    base, ext = os.path.splitext(action.target)
                    counter = 1
                    while os.path.exists(new_path):
                        new_path = os.path.join(dir_name, f"{base}_{counter}{ext}")
                        counter += 1
                os.rename(action.file_entry.path, new_path)
                print(f"Renamed to: {os.path.basename(new_path)}")
            elif action.action_type == 'CHMOD':
                # Conversion from format like '644' to int
                mode = int(str(action.target), 8)
                os.chmod(action.file_entry.path, mode)
                print("Permissions changed.")
            elif action.action_type == 'MOVE':
                target_path = action.target
                # Ensure target directory exists
                target_dir = os.path.dirname(target_path)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                # Handle case where target file already exists
                if os.path.exists(target_path):
                    base, ext = os.path.splitext(os.path.basename(target_path))
                    counter = 1
                    while os.path.exists(target_path):
                        target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                        counter += 1
                shutil.move(action.file_entry.path, target_path)
                print(f"Moved to: {target_path}")
            elif action.action_type == 'SKIP':
                print("Skipped (no action required).")
        except OSError as e:
            print(f"Error while executing action: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")