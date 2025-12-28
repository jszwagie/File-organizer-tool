#!/usr/bin/env python3
"""
File Consolidation and Cleaning Tool

Recursively organizes, deduplicates, and consolidates files from multiple
source directories into a single target directory.

Usage:
    python main.py <target_dir> <source_dir1> [source_dir2 ...]
"""

from src.config import load_configuration
from src.scanner import FileScanner
from src.analyzer import Analyzer
from src.executor import ActionExecutor


def main():
    """Main entry point for the file organizer tool."""
    config = load_configuration()
    
    print("=" * 50)
    print("File Consolidation and Cleaning Tool")
    print("=" * 50)
    print(f"Target directory (X): {config.target_dir}")
    print(f"Source directories (Y): {', '.join(config.source_dirs)}")
    print()

    # Phase 1: Scan
    print("Scanning directories...")
    scanner = FileScanner()
    all_files = scanner.scan([config.target_dir] + config.source_dirs)
    print(f"Found {len(all_files)} file(s)")
    
    for error in scanner.get_errors():
        print(f"  Warning: {error}")

    # Phase 2: Analyze
    print("\nAnalyzing files...")
    analyzer = Analyzer(config)
    suggestions = analyzer.analyze(all_files, config.target_dir)
    
    # Phase 3: Execute
    executor = ActionExecutor()
    executor.process_suggestions(suggestions)

    print("\n" + "=" * 50)
    print("Finished")
    print("=" * 50)


if __name__ == "__main__":
    main()
