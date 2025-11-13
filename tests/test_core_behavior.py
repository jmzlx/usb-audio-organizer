"""
High-quality behavior tests for core functionality.

Tests focus on contracts and behavior, not implementation details.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys


class TestCLIContract:
    """Test CLI interface contracts and behavior."""
    
    def test_cli_accepts_critical_arguments(self):
        """Verify CLI accepts and routes key arguments correctly."""
        from shokz_sync.cli import main
        
        test_cases = [
            # (args, expected_mountpoint, expected_bitrate, expected_dry_run)
            (['shokz-sync'], '/Volumes/XTRAINERZ', '96k', False),
            (['shokz-sync', 'sync', '--mountpoint', '/Volumes/TEST'], '/Volumes/TEST', '96k', False),
            (['shokz-sync', 'sync', '--bitrate', '128k'], '/Volumes/XTRAINERZ', '128k', False),
            (['shokz-sync', 'sync', '--dry-run'], '/Volumes/XTRAINERZ', '96k', True),
        ]
        
        for argv, expected_mount, expected_bitrate, expected_dry in test_cases:
            with patch.object(sys, 'argv', argv):
                with patch('shokz_sync.cli.sync_shokz') as mock_sync:
                    mock_sync.return_value = 0
                    
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    assert mock_sync.called, f"sync_shokz not called for {argv}"
                    args = mock_sync.call_args[0][0]
                    assert args.mountpoint == expected_mount
                    assert args.bitrate == expected_bitrate
                    assert args.dry_run == expected_dry
    
    def test_cli_subcommands_route_correctly(self):
        """Verify subcommands route to correct handlers."""
        from shokz_sync.cli import main
        
        test_cases = [
            (['shokz-sync', 'init-config'], 'init_config'),
            (['shokz-sync', 'show-config'], 'show_config'),
        ]
        
        for argv, expected_handler in test_cases:
            with patch.object(sys, 'argv', argv):
                with patch(f'shokz_sync.cli.{expected_handler}') as mock_handler:
                    mock_handler.return_value = 0
                    
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    assert mock_handler.called, f"{expected_handler} not called for {argv}"


class TestConfigurationManagement:
    """Test configuration creation and validation behavior."""
    
    def test_config_lifecycle(self, tmp_path):
        """Test complete config lifecycle: create, load, verify."""
        from shokz_sync.beets_config import (
            create_beets_config,
            load_beets_config,
            verify_beets_config,
        )
        
        config_path = tmp_path / 'config.yaml'
        
        # Should not exist initially
        assert not verify_beets_config(config_path)
        
        # Create config
        result_path = create_beets_config(
            config_path=config_path,
            mountpoint='/Volumes/TEST',
            bitrate='128k',
            max_bitrate=256
        )
        
        assert result_path == config_path
        assert config_path.exists()
        
        # Should now be valid
        assert verify_beets_config(config_path)
        
        # Should load with correct values
        config = load_beets_config(config_path)
        assert config['directory'] == '/Volumes/TEST'
        assert config['convert']['max_bitrate'] == 256
        assert '128k' in config['convert']['opts']
    
    def test_config_contains_required_structure(self, tmp_path):
        """Verify generated config has all required elements for beets."""
        from shokz_sync.beets_config import create_beets_config, load_beets_config
        
        config_path = tmp_path / 'config.yaml'
        create_beets_config(config_path=config_path)
        config = load_beets_config(config_path)
        
        # Required top-level keys
        required_keys = ['directory', 'library', 'import', 'paths', 'plugins']
        for key in required_keys:
            assert key in config, f"Missing required key: {key}"
        
        # Required path templates
        assert 'default' in config['paths']
        assert 'comp' in config['paths']
        
        # Should have necessary plugins
        assert 'convert' in config['plugins']
        assert 'scrub' in config['plugins']


class TestDeviceManagement:
    """Test device detection and management behavior."""
    
    SAMPLE_DISKUTIL_OUTPUT = """
   Device Node:              /dev/disk4s1
   Volume Name:              XTRAINERZ
   Mounted:                  Yes
   Mount Point:              /Volumes/XTRAINERZ
   File System Personality:  MS-DOS FAT32
"""
    
    def test_device_detection_extracts_critical_info(self):
        """Verify we can extract device node from diskutil output."""
        from shokz_sync.diskutil_utils import get_device_node
        
        with patch('shokz_sync.diskutil_utils.run_command') as mock_run:
            mock_run.return_value = Mock(stdout=self.SAMPLE_DISKUTIL_OUTPUT)
            
            device = get_device_node('/Volumes/XTRAINERZ')
            
            assert device == '/dev/disk4s1'
            mock_run.assert_called_once()
    
    def test_device_detection_handles_missing_device(self):
        """Verify proper error when device not found."""
        from shokz_sync.diskutil_utils import get_device_node, DiskutilError
        
        with patch('shokz_sync.diskutil_utils.run_command') as mock_run:
            mock_run.return_value = Mock(stdout="")
            
            with pytest.raises(DiskutilError):
                get_device_node('/Volumes/NONEXISTENT')
    
    def test_raw_device_conversion(self):
        """Verify device node to raw device node conversion."""
        from shokz_sync.diskutil_utils import get_raw_device_node
        
        # Test various disk numbers
        assert get_raw_device_node('/dev/disk4s1') == '/dev/rdisk4s1'
        assert get_raw_device_node('/dev/disk10s1') == '/dev/rdisk10s1'
        
        # Should be idempotent
        assert get_raw_device_node('/dev/rdisk4s1') == '/dev/rdisk4s1'


class TestDependencyChecking:
    """Test dependency verification behavior."""
    
    def test_all_required_commands_checked(self):
        """Verify all critical dependencies are checked."""
        from shokz_sync.dependencies import check_all_dependencies, REQUIRED_COMMANDS
        
        with patch('shokz_sync.dependencies.verify_command_works') as mock_verify:
            mock_verify.return_value = True
            
            results = check_all_dependencies()
            
            # Should check all critical tools
            critical_tools = {'beet', 'ffmpeg', 'ffprobe', 'fatsort', 'diskutil'}
            assert critical_tools.issubset(set(results.keys()))
    
    def test_missing_dependencies_detected(self):
        """Verify missing dependencies are properly reported."""
        from shokz_sync.dependencies import verify_dependencies
        
        with patch('shokz_sync.dependencies.check_all_dependencies') as mock_check:
            # Simulate missing beets and fatsort
            mock_check.return_value = {
                'beet': False,
                'ffmpeg': True,
                'ffprobe': True,
                'fatsort': False,
                'diskutil': True,
            }
            
            # Should return False when dependencies missing
            assert verify_dependencies() is False


class TestFileScanning:
    """Test file scanning behavior."""
    
    def test_scans_all_music_formats(self, tmp_path):
        """Verify scanner finds all supported music formats."""
        from shokz_sync.cli import count_music_files
        
        # Create various file types
        music_files = ['song.mp3', 'track.m4a', 'audio.flac', 'tune.ogg', 'beat.aac']
        non_music = ['readme.txt', 'cover.jpg', 'info.pdf']
        
        for file in music_files:
            (tmp_path / file).touch()
        for file in non_music:
            (tmp_path / file).touch()
        
        count = count_music_files(str(tmp_path))
        
        assert count == len(music_files), "Should count all music files"
    
    def test_scans_recursively(self, tmp_path):
        """Verify scanner finds files in nested directories."""
        from shokz_sync.cli import count_music_files
        
        # Create nested structure
        (tmp_path / 'root.mp3').touch()
        
        level1 = tmp_path / 'level1'
        level1.mkdir()
        (level1 / 'song1.mp3').touch()
        
        level2 = level1 / 'level2'
        level2.mkdir()
        (level2 / 'song2.mp3').touch()
        
        deep = tmp_path / 'a' / 'b' / 'c' / 'd'
        deep.mkdir(parents=True)
        (deep / 'deep.mp3').touch()
        
        count = count_music_files(str(tmp_path))
        
        assert count == 4, "Should find files at any depth"
    
    def test_handles_empty_directories(self, tmp_path):
        """Verify scanner handles empty directories gracefully."""
        from shokz_sync.cli import count_music_files
        
        # Create empty nested structure
        (tmp_path / 'empty' / 'nested' / 'dirs').mkdir(parents=True)
        
        # One music file elsewhere
        (tmp_path / 'song.mp3').touch()
        
        count = count_music_files(str(tmp_path))
        
        assert count == 1


class TestFatsortIntegration:
    """Test fatsort integration behavior."""
    
    def test_fatsort_converts_to_raw_device(self):
        """Verify fatsort uses raw device node."""
        from shokz_sync.fatsort_utils import run_fatsort
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            # Pass regular device, should convert to raw
            run_fatsort('/dev/disk4s1', use_sudo=True)
            
            call_args = mock_run.call_args[0][0]
            assert '/dev/rdisk4s1' in call_args, "Should use raw device"
            assert 'sudo' in call_args, "Should use sudo"
    
    def test_fatsort_detects_availability(self):
        """Verify fatsort availability check works."""
        from shokz_sync.fatsort_utils import check_fatsort_available
        
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/local/bin/fatsort'
            assert check_fatsort_available() is True
            
            mock_which.return_value = None
            assert check_fatsort_available() is False


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""
    
    def test_mixed_folder_structure(self, tmp_path):
        """Test handling of typical messy XTRAINERZ structure."""
        from shokz_sync.cli import count_music_files
        
        # Simulate real-world mess:
        # - Some albums at root
        # - Some in Artist/Album structure
        # - Some deeply nested from downloads
        # - Some multi-disc with subfolders
        
        (tmp_path / 'Blur - Think Tank' / 'track.mp3').parent.mkdir()
        (tmp_path / 'Blur - Think Tank' / 'track.mp3').touch()
        
        (tmp_path / 'The Beatles' / 'Abbey Road' / '01.mp3').parent.mkdir(parents=True)
        (tmp_path / 'The Beatles' / 'Abbey Road' / '01.mp3').touch()
        
        (tmp_path / 'Downloads' / 'Music' / '2003' / 'album' / 'song.mp3').parent.mkdir(parents=True)
        (tmp_path / 'Downloads' / 'Music' / '2003' / 'album' / 'song.mp3').touch()
        
        (tmp_path / 'Greatest Hits' / 'Disc 1' / 'track1.mp3').parent.mkdir(parents=True)
        (tmp_path / 'Greatest Hits' / 'Disc 1' / 'track1.mp3').touch()
        (tmp_path / 'Greatest Hits' / 'Disc 2' / 'track2.mp3').parent.mkdir(parents=True)
        (tmp_path / 'Greatest Hits' / 'Disc 2' / 'track2.mp3').touch()
        
        count = count_music_files(str(tmp_path))
        
        # Should find all files regardless of structure
        assert count == 5
    
    def test_compilation_albums_structure(self, tmp_path):
        """Test handling of compilation albums with various structures."""
        from shokz_sync.cli import count_music_files
        
        # Flat compilation
        comp_flat = tmp_path / 'Compilation Flat'
        comp_flat.mkdir()
        (comp_flat / 'track1.mp3').touch()
        (comp_flat / 'track2.mp3').touch()
        
        # Compilation with artist subfolders
        comp_nested = tmp_path / 'Compilation Nested'
        comp_nested.mkdir()
        (comp_nested / 'Artist A' / 'song.mp3').parent.mkdir()
        (comp_nested / 'Artist A' / 'song.mp3').touch()
        (comp_nested / 'Artist B' / 'song.mp3').parent.mkdir()
        (comp_nested / 'Artist B' / 'song.mp3').touch()
        
        count = count_music_files(str(tmp_path))
        
        assert count == 4

