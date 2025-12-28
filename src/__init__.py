"""
File Organizer Tool - Source Package

Modules:
    config: Configuration loading and CLI parsing
    scanner: Directory scanning and file metadata collection
    analyzer: File analysis and action suggestion generation
    executor: Action execution with user interaction
"""

from .config import AppConfig, load_configuration
from .scanner import FileEntry, FileScanner
from .analyzer import ActionType, AnalysisMode, SuggestedAction, Analyzer
from .executor import ActionExecutor

__all__ = [
    "AppConfig",
    "load_configuration",
    "FileEntry",
    "FileScanner",
    "ActionType",
    "AnalysisMode",
    "SuggestedAction",
    "Analyzer",
    "ActionExecutor",
]
