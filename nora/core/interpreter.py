"""
NORA Action Interpreter

Parses model output to detect and extract file operations and commands.
Supports multiple formats for specifying file paths and content.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FileAction:
    """Represents a file operation extracted from model output."""
    action_type: str  # 'create', 'append', 'read', 'delete'
    path: str
    content: Optional[str] = None
    language: Optional[str] = None


@dataclass
class CommandAction:
    """Represents a command execution request."""
    command: str
    cwd: Optional[str] = None


class ActionInterpreter:
    """Interprets model output and extracts file/command actions."""

    # Pattern: # File: path/to/file.ext
    HEADER_PATTERN = re.compile(
        r'^#\s*File:\s*(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern: ```language path/to/file.ext
    FENCED_WITH_PATH = re.compile(
        r'```(\w+)?\s+(.+?)\n(.*?)```',
        re.DOTALL
    )

    # Pattern: standard code fences with File: header before
    FENCED_CODE = re.compile(
        r'```(\w+)?\n(.*?)```',
        re.DOTALL
    )

    # Pattern: <NORA_ACTION>JSON</NORA_ACTION>
    JSON_ACTION = re.compile(
        r'<NORA_ACTION>(.*?)</NORA_ACTION>',
        re.DOTALL
    )

    def __init__(self) -> None:
        """Initialize the action interpreter."""
        logger.debug("ActionInterpreter initialized")

    def extract_actions(self, text: str) -> List[FileAction]:
        """
        Extract all file actions from model output.

        Args:
            text: Model output text

        Returns:
            List of FileAction objects
        """
        actions: List[FileAction] = []

        # Try JSON actions first (highest priority)
        actions.extend(self._extract_json_actions(text))

        # Try fenced code blocks with paths
        actions.extend(self._extract_fenced_with_path(text))

        # Try header-style file declarations
        actions.extend(self._extract_header_style(text))

        logger.info(f"Extracted {len(actions)} file actions from model output")
        return actions

    def _extract_json_actions(self, text: str) -> List[FileAction]:
        """
        Extract JSON-formatted actions.

        Format:
        <NORA_ACTION>
        {
            "action": "create",
            "path": "index.html",
            "content": "<html>...</html>"
        }
        </NORA_ACTION>

        Args:
            text: Model output text

        Returns:
            List of FileAction objects
        """
        actions: List[FileAction] = []

        for match in self.JSON_ACTION.finditer(text):
            try:
                data = json.loads(match.group(1))

                action_type = data.get("action", "create")
                path = data.get("path")
                content = data.get("content")
                language = data.get("language")

                if path:
                    actions.append(FileAction(
                        action_type=action_type,
                        path=path,
                        content=content,
                        language=language
                    ))
                    logger.debug(f"Extracted JSON action: {action_type} {path}")

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in NORA_ACTION tag: {e}")
                continue

        return actions

    def _extract_fenced_with_path(self, text: str) -> List[FileAction]:
        """
        Extract fenced code blocks with file paths.

        Format:
        ```html index.html
        <html>...</html>
        ```

        Args:
            text: Model output text

        Returns:
            List of FileAction objects
        """
        actions: List[FileAction] = []

        for match in self.FENCED_WITH_PATH.finditer(text):
            language = match.group(1)
            path = match.group(2).strip()
            content = match.group(3).strip()

            # Skip if path looks like just a language identifier
            if path and not path.isalpha() and '/' in path or '.' in path:
                actions.append(FileAction(
                    action_type="create",
                    path=path,
                    content=content,
                    language=language
                ))
                logger.debug(f"Extracted fenced block with path: {path}")

        return actions

    def _extract_header_style(self, text: str) -> List[FileAction]:
        """
        Extract header-style file declarations.

        Format:
        # File: index.html
        ```html
        <html>...</html>
        ```

        Args:
            text: Model output text

        Returns:
            List of FileAction objects
        """
        actions: List[FileAction] = []

        # Split text into lines for processing
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for file header
            header_match = self.HEADER_PATTERN.match(line)
            if header_match:
                path = header_match.group(1).strip()

                # Look for code block following the header
                content_lines: List[str] = []
                i += 1

                # Skip empty lines
                while i < len(lines) and not lines[i].strip():
                    i += 1

                # Check if next line starts a code block
                if i < len(lines) and lines[i].strip().startswith('```'):
                    # Extract language if present
                    lang_line = lines[i].strip()[3:].strip()
                    language = lang_line if lang_line and not '/' in lang_line else None
                    i += 1

                    # Collect code block content
                    while i < len(lines):
                        if lines[i].strip().startswith('```'):
                            break
                        content_lines.append(lines[i])
                        i += 1

                    content = '\n'.join(content_lines).strip()

                    if content:
                        actions.append(FileAction(
                            action_type="create",
                            path=path,
                            content=content,
                            language=language
                        ))
                        logger.debug(f"Extracted header-style action: {path}")

            i += 1

        return actions

    def extract_commands(self, text: str) -> List[CommandAction]:
        """
        Extract command execution requests from model output.

        Format:
        <NORA_COMMAND>npm install</NORA_COMMAND>

        Args:
            text: Model output text

        Returns:
            List of CommandAction objects
        """
        commands: List[CommandAction] = []

        pattern = re.compile(r'<NORA_COMMAND>(.*?)</NORA_COMMAND>', re.DOTALL)

        for match in pattern.finditer(text):
            command = match.group(1).strip()

            if command:
                commands.append(CommandAction(command=command))
                logger.debug(f"Extracted command: {command}")

        return commands

    def format_system_prompt(self) -> str:
        """
        Generate a system prompt to instruct the model on action formatting.

        Returns:
            System prompt string
        """
        return """You are an AI coding assistant with the ability to create and modify files.

When generating code files, use one of these formats:

1. Header style (recommended):
# File: path/to/file.ext
```language
code content here
```

2. Inline path:
```language path/to/file.ext
code content here
```

3. JSON action (for complex operations):
<NORA_ACTION>
{
    "action": "create",
    "path": "path/to/file.ext",
    "content": "file content here",
    "language": "html"
}
</NORA_ACTION>

For commands (use sparingly):
<NORA_COMMAND>command to run</NORA_COMMAND>

Examples:
- To create an HTML file:
  # File: index.html
  ```html
  <!DOCTYPE html>
  <html>...</html>
  ```

- To create a Python script:
  # File: app.py
  ```python
  def main():
      print("Hello!")
  ```

Always specify the full relative path from the project root.
"""
