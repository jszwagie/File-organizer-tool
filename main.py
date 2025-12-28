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
from src.analyzer import Analyzer, ActionType
from src.executor import ActionExecutor


def scan_directories(config):
    """Scan all directories and return file list.
    
    Args:
        config: AppConfig object.
        
    Returns:
        list[FileEntry]: List of scanned files.
    """
    scanner = FileScanner()
    all_files = scanner.scan([config.target_dir] + config.source_dirs)
    print(f"Found {len(all_files)} file(s)")
    
    for error in scanner.get_errors():
        print(f"  Warning: {error}")
    
    return all_files


def main():
    """Main entry point for the file organizer tool."""
    config = load_configuration()
    
    print("=" * 50)
    print("File Consolidation and Cleaning Tool")
    print("=" * 50)
    print(f"Target directory (X): {config.target_dir}")
    print(f"Source directories (Y): {', '.join(config.source_dirs)}")
    
    # =================================================================
    # PHASE 1: Sanitization (RENAME, CHMOD)
    # These operations don't change file locations, safe to do first
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 1: Sanitization (rename, chmod)")
    print("-" * 50)
    
    print("\nScanning directories...")
    all_files = scan_directories(config)
    
    print("\nAnalyzing for sanitization issues...")
    analyzer = Analyzer(config)
    all_suggestions = analyzer.analyze(all_files, config.target_dir)
    
    # Filter only RENAME and CHMOD actions
    sanitization_actions = [
        s for s in all_suggestions 
        if s.action_type in (ActionType.RENAME, ActionType.CHMOD)
    ]
    
    if sanitization_actions:
        print(f"\nFound {len(sanitization_actions)} sanitization action(s).")
        executor = ActionExecutor()
        executor.process_suggestions(sanitization_actions)
    else:
        print("\nNo sanitization issues found.")
    
    # =================================================================
    # PHASE 2: Garbage collection, Deduplication, Versioning, Consolidation
    # Rescan after renames to get updated paths
    # =================================================================
    print("\n" + "-" * 50)
    print("PHASE 2: Cleanup & Consolidation (delete, move)")
    print("-" * 50)
    
    print("\nRescanning directories after sanitization...")
    all_files = scan_directories(config)
    
    print("\nAnalyzing for cleanup and consolidation...")
    analyzer = Analyzer(config)
    all_suggestions = analyzer.analyze(all_files, config.target_dir)
    
    # Filter DELETE and MOVE actions (skip RENAME/CHMOD as they're done)
    cleanup_actions = [
        s for s in all_suggestions 
        if s.action_type in (ActionType.DELETE, ActionType.MOVE, ActionType.COPY)
    ]
    
    if cleanup_actions:
        print(f"\nFound {len(cleanup_actions)} cleanup/consolidation action(s).")
        executor = ActionExecutor()
        executor.process_suggestions(cleanup_actions)
    else:
        print("\nNo cleanup or consolidation needed.")

    print("\n" + "=" * 50)
    print("Finished")
    print("=" * 50)


if __name__ == "__main__":
    main()
