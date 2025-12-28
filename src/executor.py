import os

class ActionExecutor:
    def process_suggestions(self, suggestions):
        if not suggestions:
            print("No actions to perform.")
            return

        # Variables for "always" mode
        always_delete = False
        always_rename = False

        for action in suggestions:
            print(f"\nFILE : {action.file_entry.path}")
            print(f"PROBLEM: {action.reason}")
            print(f"SUGGESTION: {action.action_type} -> {action.target if action.target else ''}")

            # If "always" was previously chosen, skip the question
            if action.action_type == 'DELETE' and always_delete:
                self._execute(action)
                continue
            
            choice = input("Choose action: [y]es, [n]o, [a]lways for this type, [q]uit: ").lower()

            if choice == 'q':
                break
            elif choice == 'a':
                if action.action_type == 'DELETE': always_delete = True
                # ... handling other "always" types ...
                self._execute(action)
            elif choice == 't':
                self._execute(action)
            else:
                print("Skipped.")

    def _execute(self, action):
        try:
            if action.action_type == 'DELETE':
                os.remove(action.file_entry.path)
                print("Deleted.")
            elif action.action_type == 'RENAME':
                dir_name = os.path.dirname(action.file_entry.path)
                new_path = os.path.join(dir_name, action.target)
                os.rename(action.file_entry.path, new_path)
                print(f"Renamed to: {action.target}")
            elif action.action_type == 'CHMOD':
                # Conversion from format like '644' to int
                mode = int(str(action.target), 8)
                os.chmod(action.file_entry.path, mode)
                print("Permissions changed.")
            # ... MOVE ...
        except Exception as e:
            print(f"Error while executing action: {e}")