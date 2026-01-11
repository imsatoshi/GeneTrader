"""File operation utilities for GeneTrader.

This module provides safe file and directory operations with proper
error handling and logging.
"""
import os
import shutil
from pathlib import Path
from typing import List, Union, Optional

from utils.logging_config import logger


def create_directories(dirs: List[Union[str, Path]]) -> List[Path]:
    """Create multiple directories if they don't exist.

    Args:
        dirs: List of directory paths to create

    Returns:
        List of successfully created directory paths

    Raises:
        PermissionError: If directory creation fails due to permissions
    """
    created: List[Path] = []
    for dir_path in dirs:
        path = Path(dir_path)
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {path}")
            created.append(path)
        except PermissionError as e:
            logger.error(f"Permission denied creating directory {path}: {e}")
            raise
        except OSError as e:
            logger.error(f"Error creating directory {path}: {e}")
    return created


def safe_remove_file(file_path: Union[str, Path]) -> bool:
    """Safely remove a file if it exists.

    Args:
        file_path: Path to the file to remove

    Returns:
        True if file was removed or didn't exist, False on error
    """
    path = Path(file_path)
    try:
        if path.exists():
            path.unlink()
            logger.debug(f"Removed file: {path}")
        return True
    except OSError as e:
        logger.error(f"Error removing file {path}: {e}")
        return False


def safe_copy_file(src: Union[str, Path], dst: Union[str, Path],
                   overwrite: bool = True) -> bool:
    """Safely copy a file with error handling.

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite if destination exists

    Returns:
        True if copy succeeded, False otherwise
    """
    src_path = Path(src)
    dst_path = Path(dst)

    try:
        if not src_path.exists():
            logger.error(f"Source file does not exist: {src_path}")
            return False

        if dst_path.exists() and not overwrite:
            logger.warning(f"Destination exists and overwrite=False: {dst_path}")
            return False

        # Create parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(src_path, dst_path)
        logger.debug(f"Copied {src_path} to {dst_path}")
        return True
    except (OSError, shutil.Error) as e:
        logger.error(f"Error copying {src_path} to {dst_path}: {e}")
        return False


def read_file_safe(file_path: Union[str, Path], default: str = "") -> str:
    """Safely read file contents with error handling.

    Args:
        file_path: Path to the file to read
        default: Default value to return on error

    Returns:
        File contents as string, or default value on error
    """
    path = Path(file_path)
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        logger.debug(f"File not found: {path}")
        return default
    except OSError as e:
        logger.error(f"Error reading file {path}: {e}")
        return default


def write_file_safe(file_path: Union[str, Path], content: str,
                    create_parents: bool = True) -> bool:
    """Safely write content to a file with error handling.

    Args:
        file_path: Path to the file to write
        content: Content to write
        create_parents: Whether to create parent directories

    Returns:
        True if write succeeded, False otherwise
    """
    path = Path(file_path)
    try:
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding='utf-8')
        logger.debug(f"Wrote {len(content)} bytes to {path}")
        return True
    except OSError as e:
        logger.error(f"Error writing to {path}: {e}")
        return False


def get_file_size(file_path: Union[str, Path]) -> Optional[int]:
    """Get file size in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes, or None if file doesn't exist
    """
    path = Path(file_path)
    try:
        return path.stat().st_size if path.exists() else None
    except OSError:
        return None
