"""
Utilities for checking required dependencies.
"""

import shutil
import subprocess
from typing import List, Dict, Optional


class DependencyError(Exception):
    """Exception raised when required dependencies are missing."""
    pass


# Required command-line tools
REQUIRED_COMMANDS = {
    'beet': {
        'name': 'beets',
        'install': 'brew install beets',
        'check_cmd': ['beet', 'version'],
    },
    'ffmpeg': {
        'name': 'ffmpeg',
        'install': 'brew install ffmpeg',
        'check_cmd': ['ffmpeg', '-version'],
    },
    'ffprobe': {
        'name': 'ffprobe (part of ffmpeg)',
        'install': 'brew install ffmpeg',
        'check_cmd': ['ffprobe', '-version'],
    },
    'fatsort': {
        'name': 'fatsort',
        'install': 'brew install fatsort',
        'check_cmd': ['fatsort', '--version'],
    },
    'diskutil': {
        'name': 'diskutil',
        'install': 'Built-in to macOS',
        'check_cmd': ['diskutil', 'list'],
    },
}


def check_command_available(command: str) -> bool:
    """
    Check if a command is available in the PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command exists, False otherwise
    """
    return shutil.which(command) is not None


def verify_command_works(command: str, check_cmd: List[str]) -> bool:
    """
    Verify that a command not only exists but also runs successfully.
    
    Args:
        command: Command name
        check_cmd: Command and args to test execution
        
    Returns:
        True if command works, False otherwise
    """
    if not check_command_available(command):
        return False
    
    try:
        subprocess.run(
            check_cmd,
            capture_output=True,
            timeout=5,
            check=False
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_all_dependencies() -> Dict[str, bool]:
    """
    Check all required dependencies.
    
    Returns:
        Dictionary mapping command names to availability status
    """
    results = {}
    for cmd, info in REQUIRED_COMMANDS.items():
        results[cmd] = verify_command_works(cmd, info['check_cmd'])
    return results


def print_missing_dependencies(missing: List[str]) -> None:
    """
    Print helpful messages about missing dependencies.
    
    Args:
        missing: List of missing command names
    """
    print("\n❌ Missing required dependencies:\n")
    
    for cmd in missing:
        info = REQUIRED_COMMANDS[cmd]
        print(f"  • {info['name']}")
        print(f"    Install: {info['install']}")
    
    print("\n💡 Quick install all with Homebrew:")
    print("    brew install beets ffmpeg fatsort")
    print()


def verify_dependencies(verbose: bool = False) -> bool:
    """
    Verify all dependencies are available.
    
    Args:
        verbose: If True, print status of all dependencies
        
    Returns:
        True if all dependencies available, False otherwise
        
    Raises:
        DependencyError: If any dependencies are missing (with helpful message)
    """
    results = check_all_dependencies()
    missing = [cmd for cmd, available in results.items() if not available]
    
    if verbose:
        print("Checking dependencies...")
        for cmd, available in results.items():
            status = "✓" if available else "✗"
            print(f"  {status} {REQUIRED_COMMANDS[cmd]['name']}")
        print()
    
    if missing:
        print_missing_dependencies(missing)
        return False
    
    return True

