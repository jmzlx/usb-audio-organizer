# Shokz Sync

A bash script toolkit to clean, organize, and sync music to **Shokz XTRAINERZ** (formerly AfterShokz) swim MP3 players using beets, ffmpeg, and fatsort.

## Overview

The Shokz XTRAINERZ is a bone conduction MP3 player with 4GB of FAT32 storage. Because it uses the FAT32 file index order for playback, manually copying music folders can result in unpredictable track order. This tool automates the entire workflow:

1. **Organize**: Use beets to normalize folder structure and filenames
2. **Compress**: Transcode to 96 kbps AAC for space efficiency
3. **Sort**: Run fatsort to ensure predictable playback order

After running the workflow, your music library will have:
- Clean structure: `Artist - Album/NN - Title.m4a`
- Consistent bitrate (default 96 kbps AAC)
- Predictable track order

## Requirements

- **macOS** (uses `diskutil` for device detection)
- **Homebrew** (for installing dependencies)

## Installation

### 1. Install system dependencies

```bash
brew install beets ffmpeg fatsort
```

### 2. Download the scripts

```bash
# Make scripts executable
chmod +x beets-encode.sh sync-device.sh
```

### 3. Optional: Install system-wide

```bash
sudo cp beets-encode.sh /usr/local/bin/beets-encode
sudo cp sync-device.sh /usr/local/bin/sync-device
```

## Quick Start

1. **Copy your music** to the source directory:

```bash
# Copy music to the project's source directory
cp -r ~/Music/* ./source/
```

2. **Encode your music**:

```bash
./beets-encode.sh
```

This will:
- Import and organize your music with beets
- Transcode to 96 kbps AAC → `./encoded/`

3. **Sync to device**:

```bash
# Connect your Shokz XTRAINERZ (mounts at /Volumes/XTRAINERZ)
./sync-device.sh /Volumes/XTRAINERZ
```

This will:
- Copy encoded files to device
- Run fatsort to optimize playback order

## Usage

### Two-Stage Workflow

The workflow is split into two stages for flexibility:

**Stage 1: Encode** (`beets-encode.sh`)
- Organizes and encodes music files
- Outputs to `./encoded/` directory

**Stage 2: Sync** (`sync-device.sh`)
- Copies encoded files to device
- Runs fatsort for correct playback order

### Basic workflow

```bash
# Step 1: Encode music
./beets-encode.sh

# Step 2: Sync to device
./sync-device.sh /Volumes/XTRAINERZ
```

### Copy from device first, then process

```bash
# Copy from device, then encode
./beets-encode.sh --from-device

# Sync back to device
./sync-device.sh /Volumes/XTRAINERZ
```

### Use custom source directory

```bash
./beets-encode.sh --source ~/Music
```

### Preview changes (dry run)

```bash
# Preview encoding
./beets-encode.sh --dry-run

# Preview sync
./sync-device.sh /Volumes/XTRAINERZ --dry-run
```

### Custom device mountpoint

```bash
./sync-device.sh /Volumes/MY_DEVICE
```

### Custom bitrate

```bash
./beets-encode.sh --bitrate 128k
```

### Verbose output

```bash
./beets-encode.sh --verbose
./sync-device.sh /Volumes/XTRAINERZ --verbose
```

## Command Reference

### beets-encode.sh

```
Usage: beets-encode.sh [OPTIONS]

Clean and encode music files using beets.

OPTIONS:
  --source DIR        Source directory (default: ./source)
  --bitrate RATE      AAC bitrate (default: 96k)
  --from-device       Copy music from device to source first
  --device PATH       Device mount point when using --from-device (default: /Volumes/XTRAINERZ)
  --dry-run           Show what would be done without making changes
  --verbose, -v       Verbose output
  --help, -h          Show this help message
```

### sync-device.sh

```
Usage: sync-device.sh DEVICE_MOUNT [OPTIONS]

Copy encoded files to device and run fatsort.

DEVICE_MOUNT is required (e.g., /Volumes/XTRAINERZ)

OPTIONS:
  --no-clear          Don't clear device before copying
  --dry-run           Show what would be done without making changes
  --verbose, -v       Verbose output
  --help, -h          Show this help message
```

## How It Works

### Staging Workflow

The tool uses a project-based workflow for safe, fast processing:

```
usb-audio-organizer/
├── source/    # Raw input files (your original music)
├── encoded/   # Transcoded 96kbps AAC (ready for device)
└── shokz_music.db  # Beets database (created automatically)
```

**Why staging?**
- All processing happens on fast local disk (not slow USB)
- Safe: device only touched at the end
- Can preview results before copying
- Easy recovery if something goes wrong
- Project-based: all files stay in the project directory

### Workflow Steps

**Stage 1: Encoding** (`beets-encode.sh`)
1. **Dependency Check** - Verify beets, ffmpeg, and related tools
2. **Create Directories** - Set up `source/` and `encoded/` folders if needed
3. **Import Music** - `beet import source/` → organizes and tags music
4. **Convert** - `beet convert` → transcode to 96k AAC → `encoded/`

**Stage 2: Syncing** (`sync-device.sh`)
5. **Verify Encoded Files** - Check that `encoded/` contains files
6. **Detect Device** - Find device node via `diskutil`
7. **Copy to Device** - `rsync encoded/` → `/Volumes/XTRAINERZ/`
8. **FAT Sort** - Unmount, sort directory entries, remount

### Beets Organization

Beets reorganizes your music according to these path templates:

```yaml
paths:
  default: $albumartist - $album/$track - $title
  singleton: $artist/$title
  comp: Compilations/$album/$track - $title
```

**Example transformation:**

Before (messy):
```
source/
  Downloads/
    Blur - (2003) Think Tank {iMog}/
      01 - Ambulance.mp3
      02 - Out of Time.mp3
```

After (organized and encoded):
```
encoded/
  Blur - Think Tank/
    01 - Ambulance.m4a  (96 kbps AAC)
    02 - Out of Time.m4a
```

### Transcoding

Files are transcoded to AAC using these settings:
- Target: 96 kbps AAC (.m4a)
- Only files above 128 kbps are converted
- Preserves metadata
- Removes embedded album art (video stream) to prevent ffmpeg issues
- Optimized for space: 96 kbps provides good quality for spoken word and music

### FAT Sorting

The tool:
1. Detects the device node (e.g., `/dev/disk4s1`)
2. Unmounts the volume
3. Runs `sudo fatsort -o a` on the raw device (`/dev/rdisk4s1`)
4. Remounts the volume

This ensures the FAT32 directory entries are sorted alphabetically, which the XTRAINERZ uses for playback order.

## Configuration

### Beets Config

The script uses a static beets configuration file at `config.yaml` in the project root. The config includes:

- **Metadata cleaning**: Scrub plugin removes unwanted tags
- **Auto-conversion**: Transcode during import
- **System file filtering**: Ignores `.Spotlight-V100`, `.Trashes`, etc.
- **Non-interactive**: Runs without prompts

To customize, edit `config.yaml` directly. See the [beets documentation](https://beets.readthedocs.io/) for all options.

### Project Directory Structure

By default, all files are stored in the project directory:

```
usb-audio-organizer/
├── source/          # Copy your raw music here
├── encoded/         # Converted AAC files ready for device
├── config.yaml      # Beets configuration
├── shokz_music.db   # Beets database (auto-created)
├── beets-encode.sh  # Encoding script
└── sync-device.sh   # Device sync script
```

To use a custom source directory:

```bash
./beets-encode.sh --source /path/to/music
```

### Performance Notes

**Typical processing times:**
- 100 songs: 5-10 minutes
- 500 songs: 20-30 minutes
- Staging on local disk is much faster than working directly on USB

**File size savings:**
- 320 kbps MP3 → 96 kbps AAC: ~70% smaller
- 256 kbps M4A → 96 kbps AAC: ~60% smaller
- 128 kbps MP3 → unchanged (below threshold)

**Storage capacity at 96 kbps AAC:**
- 4GB device ≈ 500-600 songs (assuming 3-4 min average)

## Troubleshooting

### "Resource busy" when unmounting

Close any Finder windows or apps (Music, iTunes, etc.) that are accessing the volume.

### Device not found

Verify the mount point:

```bash
ls /Volumes/
```

If your device has a different name, use:

```bash
./sync-device.sh /Volumes/YOUR_DEVICE_NAME
```

### Permission denied when running fatsort

`fatsort` requires `sudo` to access raw devices. The script will prompt for your password when needed.

### No music files found in source

Make sure you've copied music to the source directory:

```bash
ls ./source/
```

If empty, copy your music there first:

```bash
cp -r ~/Music/* ./source/
```

## Notes on XTRAINERZ

- **FAT32 only**: The device requires FAT32 formatting
- **4GB capacity**: Transcoding to 96 kbps AAC helps maximize storage
- **Playback order**: Uses FAT directory entry order, not alphabetical sorting
  - This is why `fatsort` is essential
- **No folder navigation**: The device plays all files sequentially
  - Organizing by album helps group tracks logically

## License

MIT

## Credits

Built with:
- [beets](https://beets.io/) - Music library manager
- [ffmpeg](https://ffmpeg.org/) - Audio transcoding
- [fatsort](http://fatsort.sourceforge.net/) - FAT filesystem sorter

## Links

- [beets documentation](https://beets.readthedocs.io/) - Configuration reference
