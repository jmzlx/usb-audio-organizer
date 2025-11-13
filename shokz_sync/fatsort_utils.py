"""
Utilities for running fatsort on FAT32 volumes.
"""

import subprocess
import os
from typing import Optional


class FatsortError(Exception):
    """Exception raised for fatsort-related errors."""
    pass


def run_fatsort(device_node: str, use_sudo: bool = True) -> None:
    """
    Run fatsort on a raw device node to sort FAT32 directory entries.
    
    Args:
        device_node: Raw device node (e.g., /dev/rdisk4s1)
        use_sudo: Whether to use sudo (required for raw device access)
        
    Raises:
        FatsortError: If fatsort fails
    """
    # Ensure we're using the raw device
    if '/rdisk' not in device_node:
        device_node = device_node.replace('/dev/disk', '/dev/rdisk')
    
    # Build command: fatsort -o a (sort ascending by name)
    cmd = []
    if use_sudo:
        cmd.append('sudo')
    cmd.extend(['fatsort', '-o', 'a', device_node])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check output for success indicators
        if result.returncode == 0:
            return
        
    except subprocess.CalledProcessError as e:
        error_msg = f"fatsort failed with exit code {e.returncode}"
        if e.stderr:
            error_msg += f":\n{e.stderr}"
        raise FatsortError(error_msg)
    except FileNotFoundError:
        raise FatsortError(
            "fatsort command not found. Install it with: brew install fatsort"
        )


def check_fatsort_available() -> bool:
    """
    Check if fatsort is available on the system.
    
    Returns:
        True if fatsort is available, False otherwise
    """
    import shutil
    return shutil.which('fatsort') is not None

