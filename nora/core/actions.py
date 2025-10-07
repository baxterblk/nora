"""
NORA Actions System

Provides safe, sandboxed file operations and command execution for AI models.
All operations are restricted to the project directory where NORA was launched.
"""

import logging
import os
import pathlib
import shutil
import subprocess
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class ActionsManager:
    """Manages safe file operations and command execution within project directory."""

    def __init__(self, project_root: Optional[str] = None, safe_mode: bool = True) -> None:
        """
        Initialize the actions manager.

        Args:
            project_root: Root directory for all operations (defaults to current working dir)
            safe_mode: If True, prompts before overwriting files
        """
        self.project_root = pathlib.Path(project_root or os.getcwd()).resolve()
        self.safe_mode = safe_mode
        logger.info(f"ActionsManager initialized at {self.project_root}")

    def _resolve_path(self, path: str) -> pathlib.Path:
        """
        Resolve a path relative to project root and ensure it's within bounds.

        Args:
            path: File path (relative or absolute)

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path escapes project root
        """
        # Convert to Path and resolve
        target = (self.project_root / path).resolve()

        # Security check: ensure path is within project root
        try:
            target.relative_to(self.project_root)
        except ValueError:
            raise ValueError(
                f"Path '{path}' escapes project root '{self.project_root}'"
            )

        return target

    def _confirm_overwrite(self, path: pathlib.Path) -> bool:
        """
        Confirm file overwrite with user.

        Args:
            path: File path to check

        Returns:
            True if user confirms, False otherwise
        """
        if not self.safe_mode:
            return True

        if not path.exists():
            return True

        response = input(f"File {path} already exists. Overwrite? (y/N): ").strip().lower()
        return response in ["y", "yes"]

    def create_file(self, path: str, content: str, force: bool = False) -> Tuple[bool, str]:
        """
        Create or overwrite a file with given content.

        Args:
            path: File path (relative to project root)
            content: File content
            force: If True, skip overwrite confirmation

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = self._resolve_path(path)

            # Check if overwrite is needed
            if target.exists() and not force:
                if not self._confirm_overwrite(target):
                    logger.info(f"User cancelled overwrite of {target}")
                    return False, f"Cancelled: {path}"

            # Create parent directories if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            target.write_text(content, encoding="utf-8")
            logger.info(f"Created file: {target}")

            return True, f"Created: {path}"

        except ValueError as e:
            logger.error(f"Security error creating file: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to create file {path}: {e}")
            return False, f"Error: {e}"

    def read_file(self, path: str) -> Tuple[bool, str]:
        """
        Read a file's contents.

        Args:
            path: File path (relative to project root)

        Returns:
            Tuple of (success: bool, content or error message: str)
        """
        try:
            target = self._resolve_path(path)

            if not target.exists():
                return False, f"File not found: {path}"

            if not target.is_file():
                return False, f"Not a file: {path}"

            content = target.read_text(encoding="utf-8")
            logger.info(f"Read file: {target} ({len(content)} chars)")

            return True, content

        except ValueError as e:
            logger.error(f"Security error reading file: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return False, f"Error: {e}"

    def append_file(self, path: str, content: str) -> Tuple[bool, str]:
        """
        Append content to a file.

        Args:
            path: File path (relative to project root)
            content: Content to append

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = self._resolve_path(path)

            # Create parent directories if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Append to file
            with open(target, "a", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Appended to file: {target}")
            return True, f"Appended: {path}"

        except ValueError as e:
            logger.error(f"Security error appending to file: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to append to file {path}: {e}")
            return False, f"Error: {e}"

    def list_files(self, directory: str = ".", pattern: str = "*") -> Tuple[bool, List[str]]:
        """
        List files in a directory.

        Args:
            directory: Directory path (relative to project root)
            pattern: Glob pattern for filtering (default: "*")

        Returns:
            Tuple of (success: bool, list of file paths or error message)
        """
        try:
            target = self._resolve_path(directory)

            if not target.exists():
                return False, [f"Directory not found: {directory}"]

            if not target.is_dir():
                return False, [f"Not a directory: {directory}"]

            # List files matching pattern
            files = [
                str(p.relative_to(self.project_root))
                for p in target.glob(pattern)
                if p.is_file()
            ]

            logger.info(f"Listed {len(files)} files in {target}")
            return True, sorted(files)

        except ValueError as e:
            logger.error(f"Security error listing files: {e}")
            return False, [f"Security error: {e}"]
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            return False, [f"Error: {e}"]

    def delete_file(self, path: str, force: bool = False) -> Tuple[bool, str]:
        """
        Delete a file.

        Args:
            path: File path (relative to project root)
            force: If True, skip confirmation

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = self._resolve_path(path)

            if not target.exists():
                return False, f"File not found: {path}"

            # Confirm deletion in safe mode
            if self.safe_mode and not force:
                response = input(f"Delete {path}? (y/N): ").strip().lower()
                if response not in ["y", "yes"]:
                    logger.info(f"User cancelled deletion of {target}")
                    return False, f"Cancelled: {path}"

            # Delete file
            target.unlink()
            logger.info(f"Deleted file: {target}")

            return True, f"Deleted: {path}"

        except ValueError as e:
            logger.error(f"Security error deleting file: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False, f"Error: {e}"

    def run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
        allow_dangerous: bool = False
    ) -> Tuple[bool, str]:
        """
        Run a shell command in the project directory.

        Args:
            command: Command to execute
            cwd: Working directory (relative to project root)
            timeout: Command timeout in seconds
            allow_dangerous: If True, allows potentially dangerous commands

        Returns:
            Tuple of (success: bool, output or error message: str)
        """
        # Security check: block dangerous commands unless explicitly allowed
        dangerous_patterns = ["rm -rf", "sudo", "chmod", "chown", ">", ">>"]
        if not allow_dangerous:
            for pattern in dangerous_patterns:
                if pattern in command.lower():
                    logger.warning(f"Blocked potentially dangerous command: {command}")
                    return False, f"Blocked dangerous pattern: {pattern}"

        try:
            # Resolve working directory
            if cwd:
                work_dir = self._resolve_path(cwd)
            else:
                work_dir = self.project_root

            logger.info(f"Running command: {command} in {work_dir}")

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                logger.info(f"Command succeeded: {command}")
                return True, result.stdout
            else:
                logger.error(f"Command failed: {command} (code {result.returncode})")
                return False, result.stderr or result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return False, f"Command timed out after {timeout}s"
        except ValueError as e:
            logger.error(f"Security error running command: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to run command {command}: {e}")
            return False, f"Error: {e}"

    def create_directory(self, path: str) -> Tuple[bool, str]:
        """
        Create a directory.

        Args:
            path: Directory path (relative to project root)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = self._resolve_path(path)
            target.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {target}")
            return True, f"Created directory: {path}"

        except ValueError as e:
            logger.error(f"Security error creating directory: {e}")
            return False, f"Security error: {e}"
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False, f"Error: {e}"
