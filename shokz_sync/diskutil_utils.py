"""
Utilities for working with diskutil on macOS to detect, mount, and unmount volumes.
"""

import subprocess
import re
from typing import Optional, Dict


class DiskutilError(Exception):
    """Exception raised for diskutil-related errors."""
    pass


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a command and return the result.
    
    Args:
        cmd: Command and arguments as a list
        check: Whether to raise an exception on non-zero exit code
        
    Returns:
        CompletedProcess object
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        raise DiskutilError(f"Command failed: {' '.join(cmd)}\n{e.stderr}")


def get_mount_info(mountpoint: str) -> Dict[str, str]:
    """
    Get information about a mounted volume using diskutil info.
    
    Args:
        mountpoint: Path to the mount point (e.g., /Volumes/XTRAINERZ)
        
    Returns:
        Dictionary with keys like 'Device Node', 'Volume Name', etc.
        
    Raises:
        DiskutilError: If diskutil command fails or mountpoint not found
    """
    result = run_command(["diskutil", "info", mountpoint])
    
    info = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    
    if not info:
        raise DiskutilError(f"Could not get info for mountpoint: {mountpoint}")
    
    return info


def get_device_node(mountpoint: str) -> str:
    """
    Get the device node (e.g., /dev/disk4s1) for a mounted volume.
    
    Args:
        mountpoint: Path to the mount point
        
    Returns:
        Device node path
        
    Raises:
        DiskutilError: If device node cannot be determined
    """
    info = get_mount_info(mountpoint)
    device_node = info.get('Device Node')
    
    if not device_node:
        raise DiskutilError(f"Could not determine device node for {mountpoint}")
    
    return device_node


def get_raw_device_node(device_node: str) -> str:
    """
    Convert a device node to its raw equivalent.
    
    Args:
        device_node: Device node like /dev/disk4s1
        
    Returns:
        Raw device node like /dev/rdisk4s1
    """
    # Replace /dev/disk with /dev/rdisk
    raw_device = device_node.replace('/dev/disk', '/dev/rdisk')
    return raw_device


def unmount_volume(mountpoint: str) -> None:
    """
    Unmount a volume.
    
    Args:
        mountpoint: Path to the mount point
        
    Raises:
        DiskutilError: If unmount fails
    """
    try:
        result = run_command(["diskutil", "unmount", mountpoint])
        if "unmounted" not in result.stdout.lower():
            raise DiskutilError(f"Unmount may have failed: {result.stdout}")
    except DiskutilError as e:
        if "Resource busy" in str(e) or "busy" in str(e).lower():
            raise DiskutilError(
                f"Cannot unmount {mountpoint} - resource is busy.\n"
                f"Close any Finder windows or apps accessing the volume and try again."
            )
        raise


def mount_volume(device_node: str) -> None:
    """
    Mount a volume.
    
    Args:
        device_node: Device node to mount (e.g., /dev/disk4s1)
        
    Raises:
        DiskutilError: If mount fails
    """
    result = run_command(["diskutil", "mount", device_node])
    if "mounted" not in result.stdout.lower():
        raise DiskutilError(f"Mount may have failed: {result.stdout}")


def is_mounted(mountpoint: str) -> bool:
    """
    Check if a mountpoint exists and is mounted.
    
    Args:
        mountpoint: Path to check
        
    Returns:
        True if mounted, False otherwise
    """
    import os
    if not os.path.exists(mountpoint):
        return False
    
    try:
        info = get_mount_info(mountpoint)
        return info.get('Mounted') == 'Yes'
    except DiskutilError:
        return False

