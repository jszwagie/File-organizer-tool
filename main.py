from src.config import load_configuration
from src.scanner import FileScanner
from src.analyzer import Analyzer
from src.executor import ActionExecutor

def main():
    # Load configuration and user input
    config = load_configuration()
    
    print(f"--- Start organizing ---")
    print(f"Main directory (X): {config.target_dir}")
    print(f"Additional directories to scan (Y): {config.source_dirs}")

    # Scan all files in given directories
    scanner = FileScanner()
    all_files = scanner.scan([config.target_dir] + config.source_dirs)
    print(f"Total files found: {len(all_files)}")

    # Analyze and suggest actions
    analyzer = Analyzer(config)
    suggestions = analyzer.analyze(all_files, config.target_dir)

    # Perform actions based on sugestions and user confirmation
    executor = ActionExecutor()
    executor.process_suggestions(suggestions)

    print("\n--- Finished ---")

if __name__ == "__main__":
    main()