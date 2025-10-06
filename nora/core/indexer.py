"""
NORA Project Context Indexer

Recursively scans project directories and creates a searchable index
of file content, structure, and summaries for code-aware conversations.
"""

import hashlib
import json
import logging
import pathlib
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """Represents an indexed file."""
    path: str
    relative_path: str
    size: int
    hash: str
    language: str
    summary: Optional[str] = None
    content_preview: Optional[str] = None  # First 500 chars
    functions: List[str] = None  # Extracted function/class names
    imports: List[str] = None  # Extracted import statements

    def __post_init__(self):
        if self.functions is None:
            self.functions = []
        if self.imports is None:
            self.imports = []


class ProjectIndexer:
    """
    Index project files for code-aware conversations.

    Scans directories recursively, extracts metadata, and stores
    summaries in a JSON index file.
    """

    # File extensions to index
    INDEXED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "shell",
        ".md": "markdown",
        ".txt": "text",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
    }

    # Directories to skip
    SKIP_DIRS = {
        ".git",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "htmlcov",
        ".coverage",
    }

    def __init__(self, index_path: str = "~/.nora/index.json"):
        """
        Initialize the indexer.

        Args:
            index_path: Path to store the index file
        """
        self.index_path = pathlib.Path(index_path).expanduser()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"ProjectIndexer initialized with index_path: {self.index_path}")

    def index_project(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        max_file_size: int = 1024 * 1024  # 1MB
    ) -> Dict[str, Any]:
        """
        Index a project directory.

        Args:
            project_path: Path to project root
            project_name: Optional project name (defaults to directory name)
            max_file_size: Maximum file size to index (bytes)

        Returns:
            Index metadata dictionary

        Raises:
            FileNotFoundError: If project path doesn't exist
        """
        project_path = pathlib.Path(project_path).expanduser().resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        if not project_name:
            project_name = project_path.name

        logger.info(f"Indexing project: {project_name} at {project_path}")

        # Scan files
        files: List[FileEntry] = []
        total_size = 0
        skipped = 0

        for file_path in self._walk_directory(project_path):
            try:
                # Check file size
                size = file_path.stat().st_size
                if size > max_file_size:
                    logger.debug(f"Skipping large file: {file_path} ({size} bytes)")
                    skipped += 1
                    continue

                # Check extension
                ext = file_path.suffix.lower()
                if ext not in self.INDEXED_EXTENSIONS:
                    continue

                # Index file
                entry = self._index_file(file_path, project_path)
                if entry:
                    files.append(entry)
                    total_size += size

            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                skipped += 1

        # Create index metadata
        index_data = {
            "project_name": project_name,
            "project_path": str(project_path),
            "total_files": len(files),
            "total_size": total_size,
            "skipped_files": skipped,
            "languages": self._get_language_stats(files),
            "files": [asdict(f) for f in files]
        }

        logger.info(
            f"Indexed {len(files)} files "
            f"({total_size / 1024:.1f} KB total, {skipped} skipped)"
        )

        return index_data

    def save_index(self, index_data: Dict[str, Any]) -> None:
        """
        Save index to disk.

        Args:
            index_data: Index metadata from index_project()
        """
        with open(self.index_path, "w") as f:
            json.dump(index_data, f, indent=2)

        logger.info(f"Index saved to {self.index_path}")

    def load_index(self) -> Optional[Dict[str, Any]]:
        """
        Load index from disk.

        Returns:
            Index data or None if not found
        """
        if not self.index_path.exists():
            logger.warning(f"Index file not found: {self.index_path}")
            return None

        with open(self.index_path, "r") as f:
            index_data = json.load(f)

        logger.info(f"Loaded index for project: {index_data.get('project_name')}")
        return index_data

    def search(
        self,
        query: str,
        index_data: Optional[Dict[str, Any]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search indexed files by keyword.

        Args:
            query: Search query (simple keyword search)
            index_data: Index data (loads from disk if not provided)
            max_results: Maximum results to return

        Returns:
            List of matching file entries with relevance scores
        """
        if index_data is None:
            index_data = self.load_index()
            if not index_data:
                return []

        query_lower = query.lower()
        results = []

        for file_entry in index_data.get("files", []):
            score = 0

            # Search in file path
            if query_lower in file_entry["relative_path"].lower():
                score += 10

            # Search in content preview
            if file_entry.get("content_preview"):
                if query_lower in file_entry["content_preview"].lower():
                    score += 5

            # Search in function names
            for func in file_entry.get("functions", []):
                if query_lower in func.lower():
                    score += 8

            # Search in imports
            for imp in file_entry.get("imports", []):
                if query_lower in imp.lower():
                    score += 3

            if score > 0:
                results.append({
                    **file_entry,
                    "relevance_score": score
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.info(f"Search '{query}' found {len(results)} results")
        return results[:max_results]

    def get_context_for_chat(
        self,
        query: str,
        max_files: int = 5,
        max_chars_per_file: int = 1000
    ) -> str:
        """
        Get file context for a chat query.

        Searches the index and returns formatted file content
        suitable for injection into chat prompts.

        Args:
            query: Search query
            max_files: Maximum files to include
            max_chars_per_file: Max characters per file

        Returns:
            Formatted context string
        """
        results = self.search(query, max_results=max_files)

        if not results:
            return ""

        context_parts = []
        for result in results:
            path = result["relative_path"]
            preview = result.get("content_preview", "")[:max_chars_per_file]

            context_parts.append(f"FILE: {path}\n{preview}\n")

        context = "\n---\n".join(context_parts)
        logger.debug(f"Generated context: {len(context)} characters from {len(results)} files")

        return context

    def _walk_directory(self, root: pathlib.Path) -> List[pathlib.Path]:
        """
        Walk directory recursively, respecting skip rules.

        Args:
            root: Root directory to walk

        Returns:
            List of file paths
        """
        files = []

        for path in root.rglob("*"):
            # Skip directories
            if path.is_dir():
                continue

            # Skip if any parent directory is in SKIP_DIRS
            if any(part in self.SKIP_DIRS for part in path.parts):
                continue

            files.append(path)

        return files

    def _index_file(
        self,
        file_path: pathlib.Path,
        project_root: pathlib.Path
    ) -> Optional[FileEntry]:
        """
        Index a single file.

        Args:
            file_path: Path to file
            project_root: Project root for relative path calculation

        Returns:
            FileEntry or None if indexing failed
        """
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Calculate hash
            file_hash = hashlib.md5(content.encode()).hexdigest()

            # Get language
            ext = file_path.suffix.lower()
            language = self.INDEXED_EXTENSIONS.get(ext, "unknown")

            # Extract metadata
            functions = self._extract_functions(content, language)
            imports = self._extract_imports(content, language)

            # Create preview
            preview = content[:500]
            if len(content) > 500:
                preview += "..."

            return FileEntry(
                path=str(file_path),
                relative_path=str(file_path.relative_to(project_root)),
                size=len(content),
                hash=file_hash,
                language=language,
                content_preview=preview,
                functions=functions,
                imports=imports
            )

        except Exception as e:
            logger.warning(f"Failed to index {file_path}: {e}")
            return None

    def _extract_functions(self, content: str, language: str) -> List[str]:
        """
        Extract function/class names from code.

        Simple regex-based extraction - not AST parsing.

        Args:
            content: File content
            language: Programming language

        Returns:
            List of function/class names
        """
        import re

        functions = []

        if language == "python":
            # Find def and class statements
            pattern = r"(?:def|class)\s+(\w+)"
            functions = re.findall(pattern, content)

        elif language in ["javascript", "typescript"]:
            # Find function declarations
            pattern = r"(?:function|const|let|var)\s+(\w+)\s*[=(]"
            functions = re.findall(pattern, content)

        elif language == "go":
            # Find func declarations
            pattern = r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)"
            functions = re.findall(pattern, content)

        elif language in ["java", "c", "cpp"]:
            # Find method/function declarations (simplified)
            pattern = r"(?:public|private|protected|static)?\s*\w+\s+(\w+)\s*\("
            functions = re.findall(pattern, content)

        return functions[:50]  # Limit to 50 functions

    def _extract_imports(self, content: str, language: str) -> List[str]:
        """
        Extract import statements from code.

        Args:
            content: File content
            language: Programming language

        Returns:
            List of import statements
        """
        import re

        imports = []

        if language == "python":
            # Find import statements
            pattern = r"(?:from\s+[\w.]+\s+)?import\s+[\w.,\s]+"
            imports = re.findall(pattern, content)

        elif language in ["javascript", "typescript"]:
            # Find import statements
            pattern = r"import\s+.+?from\s+['\"][\w./]+['\"]"
            imports = re.findall(pattern, content)

        elif language == "go":
            # Find import statements
            pattern = r"import\s+(?:\([\s\S]*?\)|\"[\w/]+\")"
            imports = re.findall(pattern, content)

        elif language == "java":
            # Find import statements
            pattern = r"import\s+[\w.]+;"
            imports = re.findall(pattern, content)

        return imports[:30]  # Limit to 30 imports

    def _get_language_stats(self, files: List[FileEntry]) -> Dict[str, int]:
        """
        Get statistics about languages in the index.

        Args:
            files: List of file entries

        Returns:
            Dictionary mapping language to file count
        """
        stats: Dict[str, int] = {}

        for file_entry in files:
            lang = file_entry.language
            stats[lang] = stats.get(lang, 0) + 1

        return stats
