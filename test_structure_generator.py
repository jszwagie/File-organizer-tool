#!/usr/bin/env python3
"""
Test Structure Generator

Creates a test directory structure to verify all functionalities of the
File Consolidation and Cleaning Tool:

1. Garbage Collection: empty files, temporary files (.tmp, .bak, .log, etc.)
2. Sanitization: files with bad characters, files with wrong permissions
3. Deduplication: identical files in different locations
4. Versioning: files with same name but different content

Usage:
    python test_structure_generator.py [base_dir]
    
    Default base_dir: ./test_env
"""

import os
import shutil
import stat
import sys
import time


def create_file(path, content="", mode=0o644, mtime=None):
    """Create a file with specified content, permissions and modification time.
    
    Args:
        path: File path to create.
        content: File content (default: empty).
        mode: File permissions in octal (default: 0o644).
        mtime: Modification time as Unix timestamp (default: current time).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w') as f:
        f.write(content)
    
    os.chmod(path, mode)
    
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def setup_test_environment(base_dir):
    """Create complete test environment structure.
    
    Args:
        base_dir: Base directory for test environment.
    """
    # Clean up if exists
    if os.path.exists(base_dir):
        print(f"Removing existing test directory: {base_dir}")
        shutil.rmtree(base_dir)
    
    target_dir = os.path.join(base_dir, "target_X")
    source1_dir = os.path.join(base_dir, "source_Y1")
    source2_dir = os.path.join(base_dir, "source_Y2")
    
    os.makedirs(target_dir)
    os.makedirs(source1_dir)
    os.makedirs(source2_dir)
    
    print(f"\nCreating test structure in: {base_dir}")
    print("=" * 60)
    
    # Timestamps for testing (older = smaller timestamp)
    now = time.time()
    old_time = now - 86400 * 30   # 30 days ago
    older_time = now - 86400 * 60  # 60 days ago
    
    # =========================================================================
    # 1. GARBAGE COLLECTION - Empty and temporary files
    # =========================================================================
    print("\n[1] Garbage Collection test files:")
    
    # Empty files
    create_file(os.path.join(target_dir, "empty_file.txt"), content="")
    print(f"  - Created: target_X/empty_file.txt (empty)")
    
    create_file(os.path.join(source1_dir, "another_empty.dat"), content="")
    print(f"  - Created: source_Y1/another_empty.dat (empty)")
    
    # Temporary files with various extensions
    temp_files = [
        (target_dir, "backup.bak", "backup content"),
        (target_dir, "session.tmp", "temp session data"),
        (source1_dir, "editor.swp", "swap file content"),
        (source1_dir, "debug.log", "log entries here"),
        (source2_dir, "old_backup.bak", "old backup"),
        (source2_dir, "crash.log", "crash report"),
    ]
    
    for directory, filename, content in temp_files:
        create_file(os.path.join(directory, filename), content)
        rel_dir = os.path.basename(directory)
        print(f"  - Created: {rel_dir}/{filename} (temporary)")
    
    # =========================================================================
    # 2. SANITIZATION - Bad characters and wrong permissions
    # =========================================================================
    print("\n[2] Sanitization test files:")
    
    # Files with bad characters in names (from .clean_files: : ; * ? $ # \ ' ")
    bad_char_files = [
        (target_dir, "file:with:colons.txt", "colon file"),
        (target_dir, "file;semicolon.txt", "semicolon file"),
        (source1_dir, "what?is?this.txt", "question marks"),
        (source1_dir, "money$sign.txt", "dollar sign"),
        (source1_dir, "hash#tag.txt", "hash tag"),
        (source2_dir, "quote'file.txt", "single quote"),
        (source2_dir, 'double"quote.txt', "double quote"),
    ]
    
    for directory, filename, content in bad_char_files:
        create_file(os.path.join(directory, filename), content)
        rel_dir = os.path.basename(directory)
        print(f"  - Created: {rel_dir}/{filename} (bad characters)")
    
    # Files with non-standard permissions
    perm_files = [
        (target_dir, "world_writable.txt", "sensitive data", 0o777),
        (target_dir, "executable.txt", "not really executable", 0o755),
        (source1_dir, "too_open.txt", "should be restricted", 0o666),
        (source2_dir, "group_write.txt", "group writable", 0o664),
    ]
    
    for directory, filename, content, mode in perm_files:
        create_file(os.path.join(directory, filename), content, mode=mode)
        rel_dir = os.path.basename(directory)
        print(f"  - Created: {rel_dir}/{filename} (permissions: {oct(mode)})")
    
    # =========================================================================
    # 3. DEDUPLICATION - Files with identical content
    # =========================================================================
    print("\n[3] Deduplication test files:")
    
    # Duplicate set 1: Same content, original should be the oldest
    dup1_content = "This is the original content that gets duplicated.\n" * 10
    
    create_file(os.path.join(source2_dir, "original_doc.txt"), dup1_content, mtime=older_time)
    print(f"  - Created: source_Y2/original_doc.txt (oldest - original)")
    
    create_file(os.path.join(source1_dir, "copy_of_doc.txt"), dup1_content, mtime=old_time)
    print(f"  - Created: source_Y1/copy_of_doc.txt (duplicate)")
    
    create_file(os.path.join(target_dir, "another_copy.txt"), dup1_content, mtime=now)
    print(f"  - Created: target_X/another_copy.txt (newest duplicate)")
    
    # Duplicate set 2: Binary-like content
    dup2_content = bytes(range(256)).decode('latin-1') * 100
    
    create_file(os.path.join(target_dir, "data.bin"), dup2_content, mtime=older_time)
    print(f"  - Created: target_X/data.bin (oldest - in target)")
    
    create_file(os.path.join(source1_dir, "data_backup.bin"), dup2_content, mtime=now)
    print(f"  - Created: source_Y1/data_backup.bin (duplicate)")
    
    # Duplicate set 3: Same content in subdirectories
    dup3_content = "Configuration settings\nkey=value\n" * 5
    
    subdir1 = os.path.join(source1_dir, "config")
    subdir2 = os.path.join(source2_dir, "settings")
    
    create_file(os.path.join(subdir1, "app.conf"), dup3_content, mtime=older_time)
    print(f"  - Created: source_Y1/config/app.conf (oldest)")
    
    create_file(os.path.join(subdir2, "app.conf"), dup3_content, mtime=now)
    print(f"  - Created: source_Y2/settings/app.conf (duplicate, same name)")
    
    # =========================================================================
    # 4. VERSIONING - Same name, different content
    # =========================================================================
    print("\n[4] Versioning test files:")
    
    # Version set 1: report.txt in multiple locations
    create_file(
        os.path.join(target_dir, "report.txt"),
        "Report v1 - Initial draft\nCreated long ago",
        mtime=older_time
    )
    print(f"  - Created: target_X/report.txt (v1 - oldest)")
    
    create_file(
        os.path.join(source1_dir, "report.txt"),
        "Report v2 - Updated with corrections\nSecond version",
        mtime=old_time
    )
    print(f"  - Created: source_Y1/report.txt (v2 - middle)")
    
    create_file(
        os.path.join(source2_dir, "report.txt"),
        "Report v3 - Final version\nLatest and greatest\nFully reviewed",
        mtime=now
    )
    print(f"  - Created: source_Y2/report.txt (v3 - newest)")
    
    # Version set 2: notes.md in subdirectories
    create_file(
        os.path.join(target_dir, "docs", "notes.md"),
        "# Notes\n\nOld notes from initial project",
        mtime=older_time
    )
    print(f"  - Created: target_X/docs/notes.md (old version)")
    
    create_file(
        os.path.join(source1_dir, "archive", "notes.md"),
        "# Notes\n\nUpdated notes with new information\n\n## Section 2\nMore content",
        mtime=now
    )
    print(f"  - Created: source_Y1/archive/notes.md (new version)")
    
    # =========================================================================
    # 5. NORMAL FILES - Files that should not trigger any action
    # =========================================================================
    print("\n[5] Normal files (should only trigger permission check):")
    
    normal_files = [
        (target_dir, "readme.txt", "This is a normal readme file."),
        (target_dir, "data.csv", "col1,col2,col3\n1,2,3\n4,5,6"),
        (source1_dir, "unique_file.txt", "This content is unique to source1"),
        (source2_dir, "another_unique.txt", "This content is unique to source2"),
    ]
    
    for directory, filename, content in normal_files:
        create_file(os.path.join(directory, filename), content)
        rel_dir = os.path.basename(directory)
        print(f"  - Created: {rel_dir}/{filename}")
    
    # =========================================================================
    # 6. EDGE CASES - Special scenarios
    # =========================================================================
    print("\n[6] Edge cases:")
    
    # File with spaces in name
    create_file(
        os.path.join(source1_dir, "file with spaces.txt"),
        "Testing spaces in filename"
    )
    print(f"  - Created: source_Y1/file with spaces.txt")
    
    # File with multiple extensions
    create_file(
        os.path.join(source2_dir, "archive.tar.gz.bak"),
        "Fake archive backup"
    )
    print(f"  - Created: source_Y2/archive.tar.gz.bak (temp extension)")
    
    # Very long filename
    long_name = "a" * 100 + ".txt"
    create_file(
        os.path.join(source1_dir, long_name),
        "File with very long name"
    )
    print(f"  - Created: source_Y1/{long_name[:30]}... (long name)")
    
    # File with unicode characters (these are valid, shouldn't be changed)
    create_file(
        os.path.join(target_dir, "załącznik.txt"),
        "Polish characters in filename"
    )
    print(f"  - Created: target_X/załącznik.txt (unicode)")
    
    # Hidden file (Unix style)
    create_file(
        os.path.join(source1_dir, ".hidden_config"),
        "hidden=true"
    )
    print(f"  - Created: source_Y1/.hidden_config (hidden)")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("Test environment created successfully!")
    print(f"\nTo test the tool, run:")
    print(f"  python main.py {target_dir} {source1_dir} {source2_dir}")
    print("\nExpected actions:")
    print("  - DELETE: Empty files and temporary files (.tmp, .bak, .log, .swp)")
    print("  - RENAME: Files with bad characters (: ; ? $ # ' \")")
    print("  - CHMOD: Files with non-standard permissions")
    print("  - DELETE: Duplicate files (keeping oldest)")
    print("  - MOVE: Original files from Y to X if not in X")
    print("  - MOVE/RENAME: Version conflicts (keeping newest as current)")
    print("=" * 60)
    
    return target_dir, source1_dir, source2_dir


def print_tree(directory, prefix=""):
    """Print directory tree structure.
    
    Args:
        directory: Root directory to print.
        prefix: Prefix for indentation (used in recursion).
    """
    entries = sorted(os.listdir(directory))
    
    for i, entry in enumerate(entries):
        path = os.path.join(directory, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        if os.path.isfile(path):
            size = os.path.getsize(path)
            mode = oct(stat.S_IMODE(os.stat(path).st_mode))
            print(f"{prefix}{connector}{entry} ({size}B, {mode})")
        else:
            print(f"{prefix}{connector}{entry}/")
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(path, new_prefix)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test structure generator for File Organizer Tool"
    )
    parser.add_argument(
        "base_dir",
        nargs='?',
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_env"),
        help="Base directory for test environment (default: ./test_env)"
    )
    parser.add_argument(
        "--tree", "-t",
        action="store_true",
        help="Only print directory tree, don't create/modify anything"
    )
    
    args = parser.parse_args()
    
    if args.tree:
        # Only print tree of existing directory
        if os.path.exists(args.base_dir):
            print(f"Directory structure of: {args.base_dir}")
            print("=" * 60)
            print(f"{os.path.basename(args.base_dir)}/")
            print_tree(args.base_dir)
        else:
            print(f"Error: Directory does not exist: {args.base_dir}")
            sys.exit(1)
    else:
        # Create test environment
        target, source1, source2 = setup_test_environment(args.base_dir)
        
        print("\n\nGenerated directory structure:")
        print("=" * 60)
        print(f"{os.path.basename(args.base_dir)}/")
        print_tree(args.base_dir)
