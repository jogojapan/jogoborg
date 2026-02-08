#!/usr/bin/env python3
"""Helper module for testing BackupExecutor locally with custom environment variables."""

import os
from pathlib import Path

# Get the local_test directory
LOCAL_TEST_DIR = Path(__file__).parent
PROJECT_ROOT = LOCAL_TEST_DIR.parent

def get_local_test_env_overrides(test_name=None):
    """
    Generate environment variable overrides for local testing.
    
    Args:
        test_name: Optional name to include in directory names for test isolation
    
    Returns:
        Dictionary of environment variable overrides
    """
    test_suffix = f"_{test_name}" if test_name else ""
    
    # Create test-specific directories
    test_data_dir = LOCAL_TEST_DIR / "data" / f"test{test_suffix}"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    config_dir = test_data_dir / "config"
    log_dir = test_data_dir / "logs"
    borgspace_dir = test_data_dir / "borgspace"
    
    # Create directories
    for d in [config_dir, log_dir, borgspace_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    return {
        'JOGOBORG_CONFIG_DIR': str(config_dir),
        'JOGOBORG_LOG_DIR': str(log_dir),
        'JOGOBORG_BORGSPACE_DIR': str(borgspace_dir),
        'JOGOBORG_DEBUG': 'true',  # Enable debug logging for local tests
    }

def cleanup_test_env(env_overrides):
    """Clean up test directories after tests complete."""
    config_dir = Path(env_overrides.get('JOGOBORG_CONFIG_DIR', ''))
    if config_dir.exists():
        import shutil
        shutil.rmtree(config_dir.parent, ignore_errors=True)

# Usage example:
# from local_test.test_executor import get_local_test_env_overrides
# env_overrides = get_local_test_env_overrides('my_test')
# executor = BackupExecutor(env_overrides=env_overrides)
