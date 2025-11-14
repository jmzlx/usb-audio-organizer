#!/bin/bash
#
# beets-encode.sh - Clean and encode music files using beets
#
# This script handles the first stage of the workflow:
# 1. Optionally copy music from device to source directory
# 2. Import and organize music with beets (clean metadata, folder structure)
# 3. Transcode to 96kbps AAC for space efficiency
#
# The encoded files will be placed in ./encoded/ directory

set -euo pipefail

# Get script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
SOURCE_DIR="${SCRIPT_DIR}/source"
ENCODED_DIR="${SCRIPT_DIR}/encoded"
BITRATE="96k"
BEETS_CONFIG="${SCRIPT_DIR}/config.yaml"

# Flags
DRY_RUN=0
VERBOSE=0
FROM_DEVICE=0
DEVICE_MOUNT="/Volumes/XTRAINERZ"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_step() {
    echo -e "\n${BLUE}▶${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_verbose() {
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "  ${YELLOW}→${NC} $1"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Clean and encode music files using beets.

This script organizes your music library and converts it to 96kbps AAC format.
The encoded files will be placed in ./encoded/ directory.

OPTIONS:
    --source DIR        Source directory (default: ./source)
    --bitrate RATE      AAC bitrate (default: 96k)
    --from-device       Copy music from device to source first
    --device PATH       Device mount point when using --from-device (default: /Volumes/XTRAINERZ)
    --dry-run           Show what would be done without making changes
    --verbose, -v       Verbose output
    --help, -h          Show this help message

WORKFLOW:
    1. Optionally copy music from device to source/
    2. Import music from source/ (organize + tag with beets)
    3. Convert to 96kbps AAC → encoded/

EXAMPLES:
    # Basic usage (processes ./source/)
    $(basename "$0")
    
    # Use custom source directory
    $(basename "$0") --source ~/Music
    
    # Copy from device first, then process
    $(basename "$0") --from-device
    
    # Dry run to preview changes
    $(basename "$0") --dry-run

EOF
}

# Helper functions
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

count_files() {
    find "$1" -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.aac" \) 2>/dev/null | wc -l | tr -d ' '
}

count_m4a_files() {
    find "$1" -type f -name "*.m4a" 2>/dev/null | wc -l | tr -d ' '
}

run_beets() {
    # Change to script directory to ensure relative paths in config work correctly
    cd "$SCRIPT_DIR" || exit 1
    if [[ $VERBOSE -eq 1 ]]; then
        yes y | head -1000 | beet -c "$BEETS_CONFIG" "$@" || true
    else
        yes y | head -1000 | beet -c "$BEETS_CONFIG" "$@" 2>&1 | grep -v "^Encoding\|^Copying" || true
    fi
}

# Check dependencies
check_dependencies() {
    log_step "Checking dependencies"
    
    local missing=()
    local commands=("beet" "ffmpeg" "ffprobe" "rsync")
    
    for cmd in "${commands[@]}"; do
        if command_exists "$cmd"; then
            log_verbose "$cmd: found"
        else
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required dependencies:"
        for cmd in "${missing[@]}"; do
            echo "  • $cmd"
        done
        echo ""
        echo "Install with: brew install beets ffmpeg"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} All dependencies available"
}

# Create required directories
create_directories() {
    log_step "Setting up directories"
    
    for dir in "$SOURCE_DIR" "$ENCODED_DIR"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo "  Created: $dir"
        else
            log_verbose "Exists: $dir"
        fi
    done
    
    echo -e "${GREEN}✓${NC} Directories ready"
}

# Copy from device to source
copy_from_device() {
    log_step "Copying music from device to source directory"
    
    if [[ ! -d "$DEVICE_MOUNT" ]]; then
        log_error "Device not found at: $DEVICE_MOUNT"
        exit 1
    fi
    
    local file_count
    file_count=$(count_files "$DEVICE_MOUNT")
    echo "  Found $file_count music files on device"
    
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [DRY RUN] Would copy from $DEVICE_MOUNT to $SOURCE_DIR"
        return
    fi
    
    rsync -ah --progress \
        --exclude='.Spotlight-V100' \
        --exclude='.Trashes' \
        --exclude='System Volume Information' \
        --exclude='.DS_Store' \
        "$DEVICE_MOUNT/" "$SOURCE_DIR/"
    
    echo -e "${GREEN}✓${NC} Files copied to source directory"
}

# Import music with beets
import_music() {
    log_step "Importing and organizing music with beets"
    
    local file_count
    file_count=$(count_files "$SOURCE_DIR")
    
    if [[ $file_count -eq 0 ]]; then
        log_error "No music files found in: $SOURCE_DIR"
        exit 1
    fi
    
    echo "  Found $file_count music files in source"
    
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [DRY RUN] Would run: beet -c $BEETS_CONFIG import $SOURCE_DIR"
        return
    fi
    
    if [[ $VERBOSE -eq 1 ]]; then
        run_beets import "$SOURCE_DIR"
    else
        run_beets import --quiet "$SOURCE_DIR"
    fi
    
    echo -e "${GREEN}✓${NC} Music imported and organized"
}

# Convert music to AAC
convert_music() {
    log_step "Converting music to ${BITRATE} AAC"
    
    if [[ $DRY_RUN -eq 1 ]]; then
        echo "  [DRY RUN] Would run: beet -c $BEETS_CONFIG convert -a"
        return
    fi
    
    echo "  This may take several minutes depending on library size..."
    run_beets convert -a
    
    local encoded_count
    encoded_count=$(count_m4a_files "$ENCODED_DIR")
    echo -e "${GREEN}✓${NC} Conversion complete ($encoded_count AAC files)"
}

# Verify encoded files
verify_encoded_files() {
    log_step "Verifying encoded files"
    
    local encoded_count
    encoded_count=$(count_m4a_files "$ENCODED_DIR")
    
    if [[ $encoded_count -eq 0 ]]; then
        log_error "No encoded files found in: $ENCODED_DIR"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Found $encoded_count encoded files ready for device"
}

# Main workflow
main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  Beets Encode - Clean and encode music files"
    echo "═══════════════════════════════════════════════════════════"
    
    # Check dependencies
    check_dependencies
    
    # Create required directories
    create_directories
    
    # Copy from device if requested
    if [[ $FROM_DEVICE -eq 1 ]]; then
        copy_from_device
    fi
    
    # Import and organize
    import_music
    
    # Convert to AAC
    convert_music
    
    # Verify encoded files
    verify_encoded_files
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${GREEN}✓ Encoding complete!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    local encoded_count
    encoded_count=$(count_m4a_files "$ENCODED_DIR")
    echo "  Encoded files: $encoded_count AAC tracks in $ENCODED_DIR"
    echo "  Source files: $SOURCE_DIR"
    echo ""
    echo "Next step: Run sync-device.sh to copy files to your device"
    echo ""
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --bitrate)
            BITRATE="$2"
            shift 2
            ;;
        --from-device)
            FROM_DEVICE=1
            shift
            ;;
        --device)
            DEVICE_MOUNT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            echo ""
            usage
            exit 1
            ;;
    esac
done

# Run main workflow
main

