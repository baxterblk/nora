"""
Tests for NORA Project Context Indexer

Tests ProjectIndexer with dummy Python and JavaScript files.
"""

import pytest
import json
import pathlib
from nora.core.indexer import ProjectIndexer, FileEntry


@pytest.fixture
def dummy_project(tmp_path):
    """Create a dummy project with Python and JavaScript files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create Python file
    python_file = project_dir / "module.py"
    python_file.write_text("""
import os
import sys
from typing import Dict, List

def hello_world():
    '''Say hello to the world.'''
    print("Hello, World!")

def calculate_sum(a: int, b: int) -> int:
    '''Calculate sum of two numbers.'''
    return a + b

class DataProcessor:
    '''Process data from various sources.'''

    def __init__(self, config):
        self.config = config

    def process(self, data):
        return data.upper()
""")

    # Create JavaScript file
    js_file = project_dir / "app.js"
    js_file.write_text("""
import React from 'react';
import axios from 'axios';

function App() {
    return <div>Hello, World!</div>;
}

const fetchData = async (url) => {
    const response = await axios.get(url);
    return response.data;
};

export default App;
""")

    # Create TypeScript file
    ts_file = project_dir / "utils.ts"
    ts_file.write_text("""
export interface User {
    id: number;
    name: string;
}

export function getUserName(user: User): string {
    return user.name;
}

export const formatDate = (date: Date): string => {
    return date.toISOString();
};
""")

    # Create a Go file
    go_file = project_dir / "main.go"
    go_file.write_text("""
package main

import (
    "fmt"
    "net/http"
)

func main() {
    fmt.Println("Hello, World!")
}

func handleRequest(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Request received")
}
""")

    # Create a directory to skip
    skip_dir = project_dir / "node_modules"
    skip_dir.mkdir()
    (skip_dir / "ignored.js").write_text("// This should be ignored")

    # Create __pycache__ to skip
    pycache = project_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "ignored.pyc").write_text("ignored")

    return project_dir


class TestFileEntry:
    """Tests for FileEntry dataclass."""

    def test_init(self):
        """Test FileEntry initialization."""
        entry = FileEntry(
            path="/path/to/file.py",
            relative_path="file.py",
            size=100,
            hash="abc123",
            language="python"
        )

        assert entry.path == "/path/to/file.py"
        assert entry.relative_path == "file.py"
        assert entry.size == 100
        assert entry.hash == "abc123"
        assert entry.language == "python"
        assert entry.functions == []
        assert entry.imports == []

    def test_init_with_metadata(self):
        """Test FileEntry with functions and imports."""
        entry = FileEntry(
            path="/path/to/file.py",
            relative_path="file.py",
            size=100,
            hash="abc123",
            language="python",
            functions=["func1", "func2"],
            imports=["import os", "import sys"]
        )

        assert entry.functions == ["func1", "func2"]
        assert entry.imports == ["import os", "import sys"]


class TestProjectIndexer:
    """Tests for ProjectIndexer class."""

    def test_init(self, tmp_path):
        """Test ProjectIndexer initialization."""
        index_path = tmp_path / "index.json"
        indexer = ProjectIndexer(str(index_path))

        assert indexer.index_path == index_path
        assert index_path.parent.exists()

    def test_index_project(self, dummy_project):
        """Test indexing a project."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        assert index_data["project_name"] == "test_project"
        assert index_data["project_path"] == str(dummy_project)
        assert index_data["total_files"] == 4  # Python, JS, TS, Go
        assert index_data["total_size"] > 0
        assert "languages" in index_data
        assert len(index_data["files"]) == 4

    def test_index_project_with_custom_name(self, dummy_project):
        """Test indexing with custom project name."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project), project_name="custom-name")

        assert index_data["project_name"] == "custom-name"

    def test_skip_directories(self, dummy_project):
        """Test that node_modules and __pycache__ are skipped."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        # Verify no files from node_modules or __pycache__
        file_paths = [f["relative_path"] for f in index_data["files"]]
        assert not any("node_modules" in path for path in file_paths)
        assert not any("__pycache__" in path for path in file_paths)

    def test_language_detection(self, dummy_project):
        """Test language detection for different file types."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        languages = index_data["languages"]
        assert "python" in languages
        assert "javascript" in languages
        assert "typescript" in languages
        assert "go" in languages

    def test_extract_python_functions(self, dummy_project):
        """Test extraction of Python functions."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        # Find the Python file
        python_file = next(f for f in index_data["files"] if f["language"] == "python")

        assert "hello_world" in python_file["functions"]
        assert "calculate_sum" in python_file["functions"]
        assert "DataProcessor" in python_file["functions"]

    def test_extract_python_imports(self, dummy_project):
        """Test extraction of Python imports."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        python_file = next(f for f in index_data["files"] if f["language"] == "python")

        # Check for import statements
        imports_str = " ".join(python_file["imports"])
        assert "import os" in imports_str or "import sys" in imports_str

    def test_extract_javascript_functions(self, dummy_project):
        """Test extraction of JavaScript functions."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        js_file = next(f for f in index_data["files"] if f["relative_path"] == "app.js")

        # Check for function names
        assert "App" in js_file["functions"] or "fetchData" in js_file["functions"]

    def test_extract_javascript_imports(self, dummy_project):
        """Test extraction of JavaScript imports."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        js_file = next(f for f in index_data["files"] if f["relative_path"] == "app.js")

        # Check for import statements
        imports_str = " ".join(js_file["imports"])
        assert "react" in imports_str.lower() or "axios" in imports_str.lower()

    def test_file_hash_generation(self, dummy_project):
        """Test that file hashes are generated."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        for file_entry in index_data["files"]:
            assert file_entry["hash"] is not None
            assert len(file_entry["hash"]) == 32  # MD5 hash

    def test_content_preview(self, dummy_project):
        """Test content preview generation."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        for file_entry in index_data["files"]:
            assert file_entry["content_preview"] is not None
            assert len(file_entry["content_preview"]) <= 503  # 500 chars + "..."

    def test_save_and_load_index(self, tmp_path, dummy_project):
        """Test saving and loading index."""
        index_path = tmp_path / "test_index.json"
        indexer = ProjectIndexer(str(index_path))

        # Index and save
        index_data = indexer.index_project(str(dummy_project))
        indexer.save_index(index_data)

        assert index_path.exists()

        # Load
        loaded_data = indexer.load_index()

        assert loaded_data["project_name"] == index_data["project_name"]
        assert loaded_data["total_files"] == index_data["total_files"]
        assert len(loaded_data["files"]) == len(index_data["files"])

    def test_load_nonexistent_index(self, tmp_path):
        """Test loading non-existent index."""
        index_path = tmp_path / "nonexistent.json"
        indexer = ProjectIndexer(str(index_path))

        result = indexer.load_index()
        assert result is None

    def test_search_by_filename(self, dummy_project):
        """Test searching by filename."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("module", index_data)

        assert len(results) > 0
        assert any("module.py" in r["relative_path"] for r in results)

    def test_search_by_content(self, dummy_project):
        """Test searching by file content."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("hello", index_data)

        assert len(results) > 0
        # Should find files containing "hello"

    def test_search_by_function_name(self, dummy_project):
        """Test searching by function name."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("calculate_sum", index_data)

        assert len(results) > 0
        python_result = next(r for r in results if r["language"] == "python")
        assert "calculate_sum" in python_result["functions"]

    def test_search_no_results(self, dummy_project):
        """Test search with no results."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("nonexistent_search_term_xyz", index_data)

        assert len(results) == 0

    def test_search_max_results(self, dummy_project):
        """Test search respects max_results parameter."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("import", index_data, max_results=2)

        assert len(results) <= 2

    def test_search_relevance_scoring(self, dummy_project):
        """Test that search results are sorted by relevance."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        results = indexer.search("python", index_data)

        if len(results) > 1:
            # Verify results are sorted by relevance_score descending
            scores = [r["relevance_score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_get_context_for_chat(self, dummy_project):
        """Test generating chat context from search results."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))
        indexer.save_index(index_data)

        context = indexer.get_context_for_chat("hello", max_files=2)

        assert context != ""
        assert "FILE:" in context
        # Should contain file paths and content

    def test_get_context_for_chat_no_results(self, dummy_project):
        """Test chat context with no search results."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))
        indexer.save_index(index_data)

        context = indexer.get_context_for_chat("nonexistent_xyz")

        assert context == ""

    def test_max_file_size_limit(self, tmp_path):
        """Test that large files are skipped."""
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()

        # Create a small file
        small_file = project_dir / "small.py"
        small_file.write_text("print('hello')")

        # Create a large file
        large_file = project_dir / "large.py"
        large_file.write_text("x = 1\n" * 100000)  # > 1MB

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(project_dir), max_file_size=1024)

        # Should only index small file
        assert index_data["total_files"] == 1
        assert index_data["skipped_files"] == 1

    def test_nonexistent_project_path(self):
        """Test indexing non-existent project path."""
        indexer = ProjectIndexer()

        with pytest.raises(FileNotFoundError):
            indexer.index_project("/nonexistent/path")

    def test_language_stats(self, dummy_project):
        """Test language statistics generation."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        languages = index_data["languages"]

        # Verify counts
        assert languages["python"] == 1
        assert languages["javascript"] == 1
        assert languages["typescript"] == 1
        assert languages["go"] == 1
        assert sum(languages.values()) == 4


class TestIndexerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_project(self, tmp_path):
        """Test indexing an empty project."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(empty_dir))

        assert index_data["total_files"] == 0
        assert len(index_data["files"]) == 0

    def test_binary_file_handling(self, tmp_path):
        """Test handling of binary files."""
        project_dir = tmp_path / "with_binary"
        project_dir.mkdir()

        # Create a binary file (should be ignored)
        binary_file = project_dir / "image.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        # Create a text file
        text_file = project_dir / "file.py"
        text_file.write_text("print('hello')")

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(project_dir))

        # Should only index the Python file
        assert index_data["total_files"] == 1

    def test_file_with_unicode(self, tmp_path):
        """Test handling files with unicode content."""
        project_dir = tmp_path / "unicode_project"
        project_dir.mkdir()

        unicode_file = project_dir / "unicode.py"
        unicode_file.write_text("# コメント\ndef 函数():\n    print('你好')", encoding="utf-8")

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(project_dir))

        assert index_data["total_files"] == 1
        # Should handle unicode without errors

    def test_deeply_nested_directory(self, tmp_path):
        """Test handling deeply nested directories."""
        # Create nested structure
        deep_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_dir.mkdir(parents=True)

        file_in_deep = deep_dir / "deep.py"
        file_in_deep.write_text("print('deep')")

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(tmp_path))

        assert index_data["total_files"] == 1
        assert "a/b/c/d/e/deep.py" in index_data["files"][0]["relative_path"]
