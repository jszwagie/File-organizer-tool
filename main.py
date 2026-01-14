"""
File Consolidation and Cleaning Tool

Recursively organizes, deduplicates, and consolidates files from multiple
source directories into a single target directory.

Usage:
    python main.py <target_dir> <source_dir1> [source_dir2 ...]
"""

from src.config import load_configuration
from src.scanner import FileScanner
from src.analyzer import Analyzer, AnalysisMode
from src.executor import ActionExecutor


def scan_directories(config):
    scanner = FileScanner()
    all_files = scanner.scan([config.target_dir] + config.source_dirs)
    print(f"Found {len(all_files)} file(s)")

    for error in scanner.get_errors():
        print(f"  Warning: {error}")

    return all_files


def run_phase(config, mode, phase_name):
    print("\nScanning directories...")
    all_files = scan_directories(config)

    print(f"Analyzing: {phase_name}...")
    analyzer = Analyzer(config)
    suggestions = analyzer.analyze(all_files, config.target_dir, mode)

    if suggestions:
        print(f"Found {len(suggestions)} action(s).")
        executor = ActionExecutor()
        executor.process_suggestions(suggestions)
        return True
    else:
        print("No actions needed.")
        return False


def main():
    config = load_configuration()

    print("=" * 50)
    print("File Consolidation and Cleaning Tool")
    print("=" * 50)
    print(f"Target directory (X): {config.target_dir}")
    print(f"Source directories (Y): {', '.join(config.source_dirs)}")

    # =================================================================
    # PHASE 1: Sanitization (RENAME bad chars, CHMOD permissions)
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 1: Sanitization")
    print("  - Rename files with invalid characters")
    print("  - Fix non-standard permissions")
    print("-" * 50)

    run_phase(config, AnalysisMode.SANITIZATION, "sanitization issues")

    # =================================================================
    # PHASE 2: Garbage Collection (DELETE empty/temp files)
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 2: Garbage Collection")
    print("  - Delete empty files (0 bytes)")
    print("  - Delete temporary files")
    print("-" * 50)

    run_phase(config, AnalysisMode.GARBAGE, "garbage files")

    # =================================================================
    # PHASE 3: Deduplication (DELETE duplicates, handle versions)
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 3: Deduplication & Versioning")
    print("  - Remove duplicate files (keep oldest)")
    print("  - Handle files with same name, different content")
    print("-" * 50)

    run_phase(config, AnalysisMode.DEDUPLICATION, "duplicates and versions")

    # =================================================================
    # PHASE 4: Consolidation (MOVE unique files from Y to X)
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 4: Consolidation")
    print("  - Move unique files from source to target")
    print("-" * 50)

    run_phase(config, AnalysisMode.CONSOLIDATION, "files to consolidate")

    print("\n" + "=" * 50)
    print("Finished")
    print("=" * 50)


if __name__ == "__main__":
    main()
