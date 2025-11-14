#!/bin/bash
#
# sync-device.sh - Copy encoded files to device and run fatsort
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENCODED_DIR="${SCRIPT_DIR}/encoded"
DRY_RUN=0
CLEAR_DEVICE=0

usage() {
    cat << EOF
Usage: $(basename "$0") DEVICE_MOUNT [OPTIONS]

Copy encoded files to device and run fatsort for correct playback order.

OPTIONS:
    --clear       Clear device before copying (default: don't clear)
    --dry-run     Show what would be done without making changes
    --help, -h    Show this help message

EOF
}

# Parse arguments
DEVICE_MOUNT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --clear) CLEAR_DEVICE=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --help|-h) usage; exit 0 ;;
        -*)
            echo "Error: Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [[ -z "$DEVICE_MOUNT" ]]; then
                DEVICE_MOUNT="$1"
            else
                echo "Error: Multiple device mount points specified"
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$DEVICE_MOUNT" ]]; then
    echo "Error: Device mount point is required"
    usage
    exit 1
fi

# Check dependencies
for cmd in fatsort diskutil rsync; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: Missing required command: $cmd"
        echo "Install with: brew install fatsort"
        exit 1
    fi
done

# Verify encoded files exist
if [[ ! -d "$ENCODED_DIR" ]]; then
    echo "Error: Encoded directory not found: $ENCODED_DIR"
    exit 1
fi

encoded_count=$(find "$ENCODED_DIR" -type f -name "*.m4a" 2>/dev/null | wc -l | tr -d ' ')
if [[ $encoded_count -eq 0 ]]; then
    echo "Error: No encoded files found in: $ENCODED_DIR"
    exit 1
fi

# Verify device
if [[ ! -d "$DEVICE_MOUNT" ]]; then
    echo "Error: Device not found at: $DEVICE_MOUNT"
    exit 1
fi

device_node=$(diskutil info "$DEVICE_MOUNT" | grep "Device Node:" | awk '{print $3}')
if [[ -z "$device_node" ]]; then
    echo "Error: Could not determine device node for: $DEVICE_MOUNT"
    exit 1
fi

# Copy files
echo "Copying $encoded_count files to device..."
if [[ $DRY_RUN -eq 1 ]]; then
    if [[ $CLEAR_DEVICE -eq 1 ]]; then
        echo "[DRY RUN] Would clear: $DEVICE_MOUNT"
    fi
    echo "[DRY RUN] Would copy: $ENCODED_DIR → $DEVICE_MOUNT"
else
    if [[ $CLEAR_DEVICE -eq 1 ]]; then
        rm -rf "${DEVICE_MOUNT:?}"/*
    fi
    rsync -ah --progress "$ENCODED_DIR/" "$DEVICE_MOUNT/"
fi

# Run fatsort
if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY RUN] Would unmount, fatsort, and remount device"
else
    echo "Running fatsort (requires sudo)..."
    raw_device="${device_node/\/dev\/disk/\/dev\/rdisk}"
    
    diskutil unmount "$DEVICE_MOUNT" || {
        echo "Error: Failed to unmount device. Close Finder windows and try again."
        exit 1
    }
    
    sudo fatsort -o a "$raw_device" || {
        echo "Error: Fatsort failed"
        diskutil mount "$device_node" || true
        exit 1
    }
    
    diskutil mount "$device_node" || {
        echo "Error: Failed to remount device"
        exit 1
    }
fi

final_count=$(find "$DEVICE_MOUNT" -type f -name "*.m4a" 2>/dev/null | wc -l | tr -d ' ')
echo "Sync complete! $final_count files on device."

