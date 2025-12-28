"""
Configuration module for file organizer tool.

Handles CLI argument parsing and configuration file loading.
"""

import argparse
import configparser
import os
import sys


class AppConfig:
    """Application configuration container.

    Attributes:
        target_dir: Main directory (X) where files should be consolidated.
        source_dirs: List of additional directories (Y) to scan for files.
        bad_chars: Set of characters prohibited in filenames.
        replacement: Character used to replace prohibited characters.
        temp_exts: Set of temporary file extensions to be deleted.
        default_perm: Default file permissions in octal string format.
    """

    def __init__(self, target_dir, source_dirs, settings):
        """Initialize configuration from parsed settings.

        Args:
            target_dir: Path to target directory.
            source_dirs: List of source directory paths.
            settings: ConfigParser section with settings.
        """
        self.target_dir = os.path.abspath(target_dir)
        self.source_dirs = [os.path.abspath(d) for d in source_dirs]
        self.bad_chars = set(settings.get("bad_chars", "").split())
        self.replacement = settings.get("replacement_char", "_")
        self.temp_exts = set(settings.get("temp_extensions", "").split())
        self.default_perm = settings.get("default_permissions", "644")


def load_configuration():
    """Parse CLI arguments and load configuration file.

    Returns:
        AppConfig: Populated configuration object.

    Exits:
        With code 1 if configuration file is not found or invalid.
    """
    parser = argparse.ArgumentParser(
        description="File consolidation and cleaning tool",
        epilog="Example: python main.py /target/dir /source1 /source2",
    )
    parser.add_argument(
        "target_dir", help="Main directory (X) where files should be consolidated"
    )
    parser.add_argument(
        "source_dirs", nargs="+", help="Additional directories to scan (Y1, Y2...)"
    )
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.clean_files"),
        help="Path to configuration file (default: ~/.clean_files)",
    )

    args = parser.parse_args()

    # Try specified path, then fallback to local config
    config_path = args.config if os.path.exists(args.config) else ".clean_files"

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    config_parser = configparser.ConfigParser()
    config_parser.read(config_path)

    if "Settings" not in config_parser:
        print("Error: Configuration file missing [Settings] section")
        sys.exit(1)

    return AppConfig(args.target_dir, args.source_dirs, config_parser["Settings"])
