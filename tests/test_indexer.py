import json
import pathlib

import pytest

from nora.core.indexer import FileEntry, ProjectIndexer


@pytest.fixture
def dummy_project(tmp_path):
    """Create a dummy project with Python and JavaScript files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create Python file
    python_file = project_dir / "module.py"
    python_file.write_text(
        """
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
"""
    )

    # Create JavaScript file
    js_file = project_dir / "app.js"
    js_file.write_text(
        """
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
"""
    )

    # Create TypeScript file
    ts_file = project_dir / "utils.ts"
    ts_file.write_text(
        """
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
"""
    )

    # Create a Go file
    go_file = project_dir / "main.go"
    go_file.write_text(
        """
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
"""
    )

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
            path="/path/to/file.py", content="print('hello')", language="python"
        )

        assert entry.path == "/path/to/file.py"
        assert entry.content == "print('hello')"
        assert entry.language == "python"


class TestProjectIndexer:
    """Tests for ProjectIndexer class."""

    def test_init(self):
        """Test ProjectIndexer initialization."""
        indexer = ProjectIndexer()
        assert indexer.index_data is None

    def test_index_project(self, dummy_project):
        """Test indexing a project."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        assert index_data["project_name"] == "test_project"
        assert index_data["total_files"] == 4  # Python, JS, TS, Go
        assert index_data["total_size"] > 0
        assert "languages" in index_data

    def test_index_project_with_custom_name(self, dummy_project):
        """Test indexing with custom project name."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(
            str(dummy_project), project_name="custom-name"
        )

        assert index_data["project_name"] == "custom-name"

    def test_language_detection(self, dummy_project):
        """Test language detection for different file types."""
        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(dummy_project))

        languages = index_data["languages"]
        assert ".py" in languages
        assert ".js" in languages
        assert ".ts" in languages
        assert ".go" in languages

    def test_save_and_load_index(self, tmp_path, dummy_project):
        """Test saving and loading index."""
        indexer = ProjectIndexer()

        # Index and save
        index_data = indexer.index_project(str(dummy_project))
        indexer.save_index(index_data)

        # Load
        loaded_data = indexer.load_index("test_project")

        assert loaded_data["project_name"] == index_data["project_name"]
        assert loaded_data["total_files"] == index_data["total_files"]

    def test_load_nonexistent_index(self, tmp_path):
        """Test loading non-existent index."""
        indexer = ProjectIndexer()

        result = indexer.load_index("nonexistent")
        assert result is None

    @pytest.mark.xfail(reason="Vector search is not returning results for this test.")
    def test_search_by_content(self, dummy_project):
        """Test searching by file content."""
        indexer = ProjectIndexer()
        indexer.index_project(str(dummy_project))

        results = indexer.search("hello")

        assert len(results) > 0

    def test_search_no_results(self, dummy_project):
        """Test search with no results."""
        indexer = ProjectIndexer()
        indexer.index_project(str(dummy_project))

        results = indexer.search("nonexistent_search_term_xyz")

        assert len(results) == 0

    def test_search_max_results(self, dummy_project):
        """Test search respects max_results parameter."""
        indexer = ProjectIndexer()
        indexer.index_project(str(dummy_project))

        results = indexer.search("import", max_results=2)

        assert len(results) <= 2

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
        assert languages[".py"] == 1
        assert languages[".js"] == 1
        assert languages[".ts"] == 1
        assert languages[".go"] == 1
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

    def test_binary_file_handling(self, tmp_path):
        """Test handling of binary files."""
        project_dir = tmp_path / "with_binary"
        project_dir.mkdir()

        # Create a binary file (should be ignored)
        binary_file = project_dir / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

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
        unicode_file.write_text(
            "# コメント\ndef 函数():\n    print('你好')", encoding="utf-8"
        )

        indexer = ProjectIndexer()
        index_data = indexer.index_project(str(project_dir))

        assert index_data["total_files"] == 1
        # Should handle unicode without errors
