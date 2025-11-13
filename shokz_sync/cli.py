"""
Main CLI interface for shokz-sync.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from typing import Optional

from . import __version__
from .dependencies import verify_dependencies
from .beets_config import (
    create_beets_config,
    get_default_config_path,
    verify_beets_config,
    get_config_template,
)
from .diskutil_utils import (
    get_device_node,
    get_raw_device_node,
    unmount_volume,
    mount_volume,
    is_mounted,
    DiskutilError,
)
from .fatsort_utils import run_fatsort, FatsortError


def log_step(message: str) -> None:
    """Print a step message with formatting."""
    print(f"\n▶ {message}")


def log_success(message: str) -> None:
    """Print a success message."""
    print(f"✓ {message}")


def log_error(message: str) -> None:
    """Print an error message."""
    print(f"✗ {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """Print an info message."""
    print(f"  {message}")


def init_config(args: argparse.Namespace) -> int:
    """
    Initialize beets configuration.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    config_path = get_default_config_path()
    
    if config_path.exists() and not args.force:
        log_error(f"Config already exists: {config_path}")
        print("\nUse --force to overwrite, or edit the file manually.")
        return 1
    
    log_step("Creating beets configuration")
    
    try:
        created_path = create_beets_config(
            config_path=config_path,
            mountpoint=args.mountpoint,
            bitrate=args.bitrate,
        )
        log_success(f"Config created: {created_path}")
        
        print("\nYou can now run: shokz-sync")
        return 0
    
    except Exception as e:
        log_error(f"Failed to create config: {e}")
        return 1


def show_config(args: argparse.Namespace) -> int:
    """
    Display the config template.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print(get_config_template())
    return 0


def count_music_files(directory: str) -> int:
    """
    Count music files in a directory.
    
    Args:
        directory: Directory to scan
        
    Returns:
        Number of music files found
    """
    extensions = {'.mp3', '.m4a', '.flac', '.ogg', '.aac'}
    count = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in extensions:
                    count += 1
    except Exception:
        pass
    
    return count


def run_beets_import(
    mountpoint: str,
    config_path: Optional[Path] = None,
    dry_run: bool = False
) -> bool:
    """
    Run beets import on the mountpoint.
    
    Args:
        mountpoint: Path to the mounted volume
        config_path: Optional path to beets config
        dry_run: If True, run in pretend mode
        
    Returns:
        True if successful, False otherwise
    """
    cmd = ['beet']
    
    if config_path:
        cmd.extend(['-c', str(config_path)])
    
    cmd.append('import')
    
    if dry_run:
        cmd.append('--pretend')
    
    # Non-interactive options
    cmd.extend([
        '--quiet',  # Less verbose output
    ])
    
    cmd.append(mountpoint)
    
    log_info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        log_error("beet command not found")
        return False
    except Exception as e:
        log_error(f"Failed to run beets: {e}")
        return False


def sync_shokz(args: argparse.Namespace) -> int:
    """
    Main sync operation.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success)
    """
    mountpoint = args.mountpoint
    
    # Check dependencies
    log_step("Checking dependencies")
    if not verify_dependencies(verbose=args.verbose):
        return 1
    log_success("All dependencies available")
    
    # Verify mountpoint exists
    if not is_mounted(mountpoint):
        log_error(f"Mountpoint not found or not mounted: {mountpoint}")
        log_info("Connect your Shokz XTRAINERZ device and try again.")
        return 1
    log_success(f"Found mounted volume: {mountpoint}")
    
    # Check or create config
    config_path = get_default_config_path()
    if not verify_beets_config(config_path):
        log_info(f"No valid beets config found at {config_path}")
        log_info("Creating default configuration...")
        try:
            create_beets_config(
                config_path=config_path,
                mountpoint=mountpoint,
                bitrate=args.bitrate,
            )
            log_success(f"Config created: {config_path}")
        except Exception as e:
            log_error(f"Failed to create config: {e}")
            return 1
    else:
        log_success(f"Using config: {config_path}")
    
    # Count files before
    files_before = count_music_files(mountpoint)
    log_info(f"Music files on device: {files_before}")
    
    # Run beets import
    log_step("Running beets import to organize and clean library")
    if args.dry_run:
        log_info("DRY RUN MODE - no changes will be made")
    
    success = run_beets_import(
        mountpoint=mountpoint,
        config_path=config_path,
        dry_run=args.dry_run
    )
    
    if not success:
        log_error("Beets import failed")
        return 1
    log_success("Beets import completed")
    
    # If dry run, stop here
    if args.dry_run:
        log_info("Dry run complete - no fatsort performed")
        return 0
    
    # Get device information for fatsort
    log_step("Preparing to run fatsort")
    try:
        device_node = get_device_node(mountpoint)
        raw_device = get_raw_device_node(device_node)
        log_info(f"Device node: {device_node}")
        log_info(f"Raw device: {raw_device}")
    except DiskutilError as e:
        log_error(f"Failed to get device info: {e}")
        return 1
    
    # Unmount
    log_step("Unmounting volume")
    try:
        unmount_volume(mountpoint)
        log_success("Volume unmounted")
    except DiskutilError as e:
        log_error(str(e))
        return 1
    
    # Run fatsort
    log_step("Running fatsort to optimize playback order")
    log_info("This may take a moment and requires sudo access...")
    try:
        run_fatsort(raw_device, use_sudo=True)
        log_success("Fatsort completed")
    except FatsortError as e:
        log_error(f"Fatsort failed: {e}")
        # Try to remount anyway
        try:
            mount_volume(device_node)
        except DiskutilError:
            pass
        return 1
    
    # Remount
    log_step("Remounting volume")
    try:
        mount_volume(device_node)
        log_success(f"Volume remounted at {mountpoint}")
    except DiskutilError as e:
        log_error(f"Failed to remount: {e}")
        log_info("You may need to manually remount or reconnect the device.")
        return 1
    
    # Final summary
    files_after = count_music_files(mountpoint)
    
    print("\n" + "="*60)
    print("✓ Sync complete!")
    print("="*60)
    print(f"  Mountpoint: {mountpoint}")
    print(f"  Device: {device_node}")
    print(f"  Music files: {files_after}")
    print()
    
    return 0


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog='shokz-sync',
        description='Organize and compress music on Shokz XTRAINERZ using beets + ffmpeg + fatsort',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  shokz-sync                          # Sync with default settings
  shokz-sync --dry-run                # Preview changes without modifying files
  shokz-sync --bitrate 128k           # Use 128 kbps AAC encoding
  shokz-sync --mountpoint /Volumes/MY_DEVICE
  shokz-sync init-config              # Create default beets config
  shokz-sync show-config              # Display config template
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Sync command (default)
    sync_parser = subparsers.add_parser(
        'sync',
        help='Sync and organize music (default command)'
    )
    sync_parser.add_argument(
        '--mountpoint',
        default='/Volumes/XTRAINERZ',
        help='Mount point of the Shokz device (default: /Volumes/XTRAINERZ)'
    )
    sync_parser.add_argument(
        '--bitrate',
        default='96k',
        help='Target AAC bitrate for transcoding (default: 96k)'
    )
    sync_parser.add_argument(
        '--no-convert',
        action='store_true',
        help='Skip transcoding, only reorganize'
    )
    sync_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    sync_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    # Init-config command
    init_parser = subparsers.add_parser(
        'init-config',
        help='Create default beets configuration'
    )
    init_parser.add_argument(
        '--mountpoint',
        default='/Volumes/XTRAINERZ',
        help='Mount point for config (default: /Volumes/XTRAINERZ)'
    )
    init_parser.add_argument(
        '--bitrate',
        default='96k',
        help='Target bitrate (default: 96k)'
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing config'
    )
    
    # Show-config command
    show_parser = subparsers.add_parser(
        'show-config',
        help='Display config template'
    )
    
    args = parser.parse_args()
    
    # Default to sync if no command specified
    if not args.command:
        args.command = 'sync'
        args.mountpoint = '/Volumes/XTRAINERZ'
        args.bitrate = '96k'
        args.no_convert = False
        args.dry_run = False
        args.verbose = False
    
    # Route to appropriate handler
    if args.command == 'init-config':
        exit_code = init_config(args)
    elif args.command == 'show-config':
        exit_code = show_config(args)
    else:  # sync
        exit_code = sync_shokz(args)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

