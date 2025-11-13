# Shokz Sync

A CLI tool to clean, compress, and sort music on **Shokz XTRAINERZ** (formerly AfterShokz) swim MP3 players using beets, ffmpeg, and fatsort.

## Overview

The Shokz XTRAINERZ is a bone conduction MP3 player with 4GB of FAT32 storage. Because it uses the FAT32 file index order for playback, manually copying music folders can result in unpredictable track order. This tool automates the entire workflow:

1. **Organize**: Use beets to normalize folder structure and filenames
2. **Compress**: Transcode high-bitrate files to AAC for space efficiency
3. **Sort**: Run fatsort to ensure predictable playback order

After running `shokz-sync`, your music library will have:
- Clean structure: `Artist - Album/NN - Title.ext`
- Consistent bitrate (default 96 kbps AAC)
- Predictable track order

## Requirements

- **macOS** (uses `diskutil` for device detection)
- **Homebrew** (for installing dependencies)
- **Python 3.8+**
- **uv** (recommended package manager - 10x faster than pip)

## Installation

### 1. Install system dependencies

```bash
brew install beets ffmpeg fatsort
```

### 2. Install uv (recommended)

[uv](https://github.com/astral-sh/uv) is a blazingly fast Python package manager written in Rust (10-100x faster than pip):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via Homebrew:

```bash
brew install uv
```

**Why uv?**
- ⚡ 10-100x faster than pip
- 🔒 Better dependency resolution
- 🛠️ Drop-in pip replacement
- 📦 Built-in tool isolation

If you prefer traditional pip, it will work too (just slower):
```bash
pip install -e .
```

### 3. Install shokz-sync

Clone this repository and install:

```bash
cd usb-audio-organizer
uv pip install -e .
```

Or use uv's tool installation:

```bash
uv tool install .
```

### 4. Verify installation

```bash
shokz-sync --version
```

## Quick Start

1. **Connect your Shokz XTRAINERZ** - it should mount at `/Volumes/XTRAINERZ`

2. **Run the sync**:

```bash
shokz-sync
```

That's it! The tool will:
- Check dependencies
- Create a beets config if needed
- Organize your music library
- Unmount the device
- Run fatsort to optimize playback order
- Remount the device

## Usage

### Basic sync

```bash
shokz-sync
```

### Preview changes (dry run)

```bash
shokz-sync --dry-run
```

### Custom mountpoint

```bash
shokz-sync --mountpoint /Volumes/MY_DEVICE
```

### Custom bitrate

```bash
shokz-sync --bitrate 128k
```

### Initialize configuration

Create a beets config file at `~/.config/beets/config.yaml`:

```bash
shokz-sync init-config
```

### View config template

```bash
shokz-sync show-config
```

## Command Reference

```
shokz-sync [command] [options]

Commands:
  sync              Sync and organize music (default)
  init-config       Create default beets configuration
  show-config       Display config template

Options for sync:
  --mountpoint PATH    Mount point of device (default: /Volumes/XTRAINERZ)
  --bitrate RATE       Target AAC bitrate (default: 96k)
  --no-convert         Skip transcoding, only reorganize
  --dry-run            Preview changes without modifying files
  --verbose, -v        Verbose output
```

## How It Works

### Nested Folder Support

**shokz-sync fully supports nested folder structures of any depth.** Whether you have:
- Flat folders at the root
- Artist/Album nesting
- Genre/Artist/Album hierarchies  
- Multi-disc albums with subfolders
- Messy mixed structures from manual copying

The tool recursively scans all subdirectories and organizes everything into a clean, consistent structure.

#### Examples of Supported Structures

**Flat structure:**
```
/Volumes/XTRAINERZ/
├── song1.mp3
├── song2.mp3
└── song3.m4a
```

**Artist/Album nesting:**
```
/Volumes/XTRAINERZ/
├── Blur/
│   └── Think Tank/
│       ├── 01.mp3
│       └── 02.mp3
└── Radiohead/
    └── OK Computer/
        ├── 01.mp3
        └── 02.mp3
```

**Multi-disc albums:**
```
/Volumes/XTRAINERZ/
└── Artist - Greatest Hits/
    ├── Disc 1/
    │   ├── 01.mp3
    │   └── 02.mp3
    └── Disc 2/
        ├── 01.mp3
        └── 02.mp3
```

**Very deep nesting (any depth works):**
```
/Volumes/XTRAINERZ/
└── Downloads/
    └── Music/
        └── 2003/
            └── Rock/
                └── Blur/
                    └── Think Tank/
                        ├── 01.mp3
                        └── 02.mp3
```

All files are found regardless of nesting depth!

### 1. Dependency Check

The tool verifies that all required commands are available:
- `beet` (beets music tagger)
- `ffmpeg` & `ffprobe` (audio transcoding)
- `fatsort` (FAT filesystem sorter)
- `diskutil` (macOS disk utility)

### 2. Beets Organization

Beets reorganizes your music according to these path templates:

```yaml
paths:
  default: $albumartist - $album/$track - $title
  singleton: $artist/$title
  comp: Compilations/$album/$track - $title
```

**Example transformation:**

Before (nested and messy):
```
/Volumes/XTRAINERZ/
  Downloads/
    Music/
      Blur - (2003) Think Tank {iMog}/
        01 - Ambulance.mp3
        02 - Out of Time.mp3
  [PMEDIA] ⭐/
    Some Folder/
      track1.m4a
```

After (clean and organized):
```
/Volumes/XTRAINERZ/
  Blur - Think Tank/
    01 - Ambulance.m4a
    02 - Out of Time.m4a
  Artist Name - Album Name/
    01 - Track Name.m4a
```

**Note:** All files are found regardless of nesting depth!

### 3. Transcoding

Files above 128 kbps are automatically transcoded to AAC:
- Default target: 96 kbps AAC (.m4a)
- Preserves metadata and album art
- Skips files already at low bitrate

### 4. FAT Sorting

The tool:
1. Detects the device node (e.g., `/dev/disk4s1`)
2. Unmounts the volume
3. Runs `fatsort -o a` on the raw device (`/dev/rdisk4s1`)
4. Remounts the volume

This ensures the FAT32 directory entries are sorted alphabetically, which the XTRAINERZ uses for playback order.

## Configuration

### Beets Config Location

Default: `~/.config/beets/config.yaml`

The tool will automatically create a config optimized for the XTRAINERZ if one doesn't exist.

### Customizing the Config

Edit `~/.config/beets/config.yaml` to customize:

- **Path templates**: Change how folders/files are named
- **Plugins**: Enable features like `fetchart`, `embedart`, `lastgenre`
- **Transcoding**: Adjust bitrate, format, or quality settings

See the [beets documentation](https://beets.readthedocs.io/) for full config options.

#### Advanced Customization Examples

**Genre-based organization:**
```yaml
paths:
  default: $genre/$albumartist - $album/$track - $title
  comp: Compilations/$album/$track - $title

plugins:
  - scrub
  - convert
  - lastgenre  # Auto-fetch genres

lastgenre:
  auto: yes
```

**Classical music by composer:**
```yaml
paths:
  default: $albumartist - $album/$track - $title
  classical: Classical/$composer/$album/$track - $title
  comp: Compilations/$album/$track - $title
```

**Automatic album art:**
```yaml
plugins:
  - scrub
  - convert
  - fetchart  # Download album art
  - embedart  # Embed in files

fetchart:
  auto: yes

embedart:
  auto: yes
```

**Less interactive imports:**
```yaml
import:
  quiet_fallback: skip  # Skip untagged items automatically
  timid: no             # Don't ask for confirmation
  incremental: yes      # Only import new files
```

### Sample Config

```yaml
directory: /Volumes/XTRAINERZ
library: ~/.config/beets/shokz_music.db

import:
  move: yes
  copy: no
  write: yes
  autotag: yes
  incremental: yes

paths:
  default: $albumartist - $album/%if{$track,$track - }$title
  singleton: $artist/$title
  comp: Compilations/$album/%if{$track,$track - }$title

plugins:
  - scrub
  - convert

convert:
  auto: no
  copy_album_art: yes
  max_bitrate: 128
  format: aac
  opts: '-b:a 96k'
```

## Usage Examples

### Example 1: First-Time Setup

You just got your XTRAINERZ and dragged some music onto it:

**Before:**
```
/Volumes/XTRAINERZ/
├── Blur - (2003) Think Tank {iMog}/
│   ├── 01-ambulance.mp3 (320 kbps)
│   └── 02-out of time.mp3 (320 kbps)
└── [PMEDIA] The Beatles ⭐/
    └── track01.m4a (256 kbps)
```

**Run:**
```bash
shokz-sync
```

**After:**
```
/Volumes/XTRAINERZ/
├── Blur - Think Tank/
│   ├── 01 - Ambulance.m4a (96 kbps)
│   └── 02 - Out of Time.m4a (96 kbps)
└── The Beatles - Abbey Road/
    └── 01 - Come Together.m4a (96 kbps)
```

### Example 2: Adding New Albums

```bash
# Copy new folders to the device
cp -r ~/Music/NewAlbum1 /Volumes/XTRAINERZ/
cp -r ~/Music/NewAlbum2 /Volumes/XTRAINERZ/

# Preview what will happen
shokz-sync --dry-run

# Run actual sync (only new files processed)
shokz-sync
```

### Example 3: Higher Quality

For audiobooks or classical music where you want better quality:

```bash
shokz-sync --bitrate 128k
```

### Example 4: Organization Only

You already have optimized files and just want clean organization:

```bash
shokz-sync --no-convert
```

### Example 5: Custom Device Name

Your device is named something else:

```bash
# Check what it's called
ls /Volumes/

# Sync with custom mountpoint
shokz-sync --mountpoint /Volumes/SHOKZ
```

## Workflow

### Initial Setup

1. Copy all your existing music to `/Volumes/XTRAINERZ` however you like
2. Run `shokz-sync` once to organize everything

### Adding New Music

1. Copy new album folders to `/Volumes/XTRAINERZ`
2. Run `shokz-sync` again
3. Beets will process only the new files (thanks to `incremental: yes`)

### Performance Notes

**Typical sync times:**
- 100 songs (no transcoding): 1-2 minutes
- 100 songs (with transcoding): 5-10 minutes
- 500 songs (mixed): 15-30 minutes

**File size savings:**
- 320 kbps MP3 → 96 kbps AAC: ~70% smaller
- 256 kbps M4A → 96 kbps AAC: ~60% smaller
- 128 kbps MP3 → unchanged (below threshold)

**Storage capacity at 96 kbps AAC:**
- 4GB device ≈ 500-600 songs (assuming 3-4 min average)

## Troubleshooting

### "Resource busy" when unmounting

Close any Finder windows or apps (Music, iTunes, etc.) that are accessing the volume.

### Device not found at `/Volumes/XTRAINERZ`

Verify the mount point:

```bash
ls /Volumes/
```

If your device has a different name, use:

```bash
shokz-sync --mountpoint /Volumes/YOUR_DEVICE_NAME
```

### Beets import hanging

If beets asks questions interactively, respond to them. Or adjust the `import` section in your config to be more automatic:

```yaml
import:
  quiet_fallback: skip
  timid: no
```

### Permission denied when running fatsort

`fatsort` requires `sudo` to access raw devices. The tool will prompt for your password when needed.

### Files not transcoding

Check the `convert` plugin in your beets config. The tool runs beets import without auto-conversion to give you more control. To enable auto-conversion:

```yaml
convert:
  auto: yes
```

Or manually trigger conversion after organizing:

```bash
beet convert
```

## Notes on XTRAINERZ

- **FAT32 only**: The device requires FAT32 formatting
- **4GB capacity**: Transcoding to 96 kbps AAC helps maximize storage
- **Playback order**: Uses FAT directory entry order, not alphabetical sorting
  - This is why `fatsort` is essential
- **No folder navigation**: The device plays all files sequentially
  - Organizing by album helps group tracks logically

## Architecture

### System Overview

```
┌─────────────────────────────┐
│     shokz-sync CLI          │
│        (cli.py)             │
└────────────┬────────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌────┐ ┌─────────┐
│Dependencies│ │Beets│ │Diskutil│
│  Checker  │ │Config│ │ Utils  │
└────────┘ └────┘ └─────────┘
    │        │        │
    └────────┼────────┘
             ▼
    ┌────────────────┐
    │ External Tools │
    │ • beets        │
    │ • ffmpeg       │
    │ • fatsort      │
    └────────────────┘
```

### Workflow Steps

1. **Dependency Check** - Verify all required tools are available
2. **Device Detection** - Find and verify the mounted device
3. **Config Management** - Create or use existing beets config
4. **Beets Import** - Organize and transcode music files
5. **Device Node Detection** - Get raw device path via diskutil
6. **Unmount** - Safely unmount the volume
7. **FAT Sorting** - Sort directory entries alphabetically
8. **Remount** - Mount the device again

### Project Structure

```
usb-audio-organizer/
├── shokz_sync/
│   ├── __init__.py
│   ├── cli.py              # Main CLI interface & orchestration
│   ├── beets_config.py     # Beets config management
│   ├── diskutil_utils.py   # macOS diskutil wrappers
│   ├── fatsort_utils.py    # fatsort wrappers
│   └── dependencies.py     # Dependency checking
├── tests/
│   └── test_core_behavior.py  # Behavior-driven tests
├── pyproject.toml          # Package configuration
├── LICENSE                 # MIT License
└── README.md               # This file
```

## Development

### Testing Philosophy

This project uses **behavior-driven testing** with 16 high-quality tests focusing on:
- **Contracts** - What the user expects
- **Real-world scenarios** - Actual use cases
- **Integration points** - How components interact
- **Not implementation details** - Tests survive refactoring

### Running Tests

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=shokz_sync --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Test Organization

Tests are organized by behavior, not by module:
- `TestCLIContract` - User interacts with CLI
- `TestConfigurationManagement` - Config lifecycle
- `TestDeviceManagement` - Device detection
- `TestDependencyChecking` - Tool availability
- `TestFileScanning` - File discovery
- `TestFatsortIntegration` - FAT32 sorting
- `TestRealWorldScenarios` - Complex folder structures

### Development Workflow

```bash
# Clone and setup
git clone <repository-url>
cd usb-audio-organizer
brew install beets ffmpeg fatsort uv
uv pip install -e ".[dev]"

# Make changes
# ... edit code ...

# Run tests
pytest

# Install locally
uv pip install -e .

# Test with your device
shokz-sync --dry-run
```

## License

MIT

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Credits

Built with:
- [beets](https://beets.io/) - Music library manager
- [ffmpeg](https://ffmpeg.org/) - Audio transcoding
- [fatsort](http://fatsort.sourceforge.net/) - FAT filesystem sorter

## Links

- [Shokz XTRAINERZ](https://shokz.com/products/xtrainerz) - Product page
- [beets documentation](https://beets.readthedocs.io/) - Configuration reference
- [ffmpeg documentation](https://ffmpeg.org/documentation.html) - Encoding options

