import argparse
import configparser
import os
import sys

class AppConfig:
    def __init__(self, target_dir, source_dirs, settings):
        self.target_dir = target_dir
        self.source_dirs = source_dirs
        # Load settings from config file
        self.bad_chars = set(settings.get('bad_chars', '').split())
        self.replacement = settings.get('replacement_char', '_')
        self.temp_exts = set(settings.get('temp_extensions', '').split())
        self.default_perm = settings.get('default_permissions', '644')

def load_configuration():
    # Load command line arguments
    parser = argparse.ArgumentParser(description="File organizing tool")
    parser.add_argument("target_dir", help="Main directory (X) where files should go")
    parser.add_argument("source_dirs", nargs='+', help="Additional directories to scan (Y1, Y2...)")
    parser.add_argument("--config", default=os.path.expanduser("~/.clean_files"), help="Path to configuration file")
    
    args = parser.parse_args()

    # Load configuration file
    config_parser = configparser.ConfigParser()
    # Fallback: search locally if not found in HOME
    config_path = args.config if os.path.exists(args.config) else '.clean_files'
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    config_parser.read(config_path)
    
    if 'Settings' not in config_parser:
        print("Error: Configuration file does not have a [Settings] section")
        sys.exit(1)

    return AppConfig(args.target_dir, args.source_dirs, config_parser['Settings'])