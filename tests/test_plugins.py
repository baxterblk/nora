"""Tests for NORA PluginLoader"""

from pathlib import Path

import pytest

from nora.core.plugins import PluginLoader


class TestPluginLoader:
    """Test suite for PluginLoader"""

    def test_init_default_path(self):
        """Test initialization with default plugins directory"""
        loader = PluginLoader()

        assert loader.plugins_dir.name == "plugins"
        assert "nora" in str(loader.plugins_dir)

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom plugins directory"""
        custom_dir = tmp_path / "custom_plugins"
        custom_dir.mkdir()

        loader = PluginLoader(custom_dir)

        assert loader.plugins_dir == custom_dir

    def test_load_plugins_empty_directory(self, tmp_path):
        """Test loading plugins from empty directory"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert plugins == {}

    def test_load_plugins_no_directory(self, tmp_path):
        """Test loading plugins when directory doesn't exist"""
        plugins_dir = tmp_path / "nonexistent"

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert plugins == {}

    def test_load_valid_plugin(self, tmp_path):
        """Test loading a valid plugin"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create a valid plugin
        plugin_file = plugins_dir / "test_plugin.py"
        plugin_content = """
def register():
    def run(model, call_fn):
        print("Test plugin running")

    return {
        "name": "test_plugin",
        "description": "A test plugin",
        "run": run
    }
"""
        plugin_file.write_text(plugin_content)

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert "test_plugin" in plugins
        assert plugins["test_plugin"]["name"] == "test_plugin"
        assert plugins["test_plugin"]["description"] == "A test plugin"
        assert callable(plugins["test_plugin"]["run"])

    def test_skip_underscore_files(self, tmp_path):
        """Test that files starting with underscore are skipped"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create an underscore file
        (plugins_dir / "_internal.py").write_text("# internal file")
        (plugins_dir / "__init__.py").write_text("# init file")

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert plugins == {}

    def test_load_plugin_no_register(self, tmp_path):
        """Test that plugins without register() function are skipped"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_file = plugins_dir / "invalid.py"
        plugin_file.write_text("def some_function(): pass")

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert plugins == {}

    def test_load_plugin_invalid_structure(self, tmp_path):
        """Test that plugins with invalid structure are skipped"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_file = plugins_dir / "invalid.py"
        plugin_content = """
def register():
    return {"invalid": "structure"}
"""
        plugin_file.write_text(plugin_content)

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert plugins == {}

    def test_load_multiple_plugins(self, tmp_path):
        """Test loading multiple plugins"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create two plugins
        for i in range(2):
            plugin_file = plugins_dir / f"plugin{i}.py"
            plugin_content = f"""
def register():
    def run(model, call_fn):
        pass

    return {{
        "name": "plugin{i}",
        "description": "Plugin {i}",
        "run": run
    }}
"""
            plugin_file.write_text(plugin_content)

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        assert len(plugins) == 2
        assert "plugin0" in plugins
        assert "plugin1" in plugins

    def test_get_plugin_exists(self, tmp_path):
        """Test getting an existing plugin"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_file = plugins_dir / "test.py"
        plugin_content = """
def register():
    def run(model, call_fn):
        pass

    return {
        "name": "test",
        "description": "Test",
        "run": run
    }
"""
        plugin_file.write_text(plugin_content)

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        plugin = loader.get_plugin("test", plugins)

        assert plugin is not None
        assert plugin["name"] == "test"

    def test_get_plugin_not_exists(self, tmp_path):
        """Test getting a non-existent plugin"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        plugin = loader.get_plugin("nonexistent", plugins)

        assert plugin is None

    def test_run_plugin_success(self, tmp_path):
        """Test running a plugin successfully"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Track if plugin was called
        called = []

        plugin_file = plugins_dir / "test.py"
        plugin_content = """
def register():
    def run(model, call_fn):
        # Plugin execution logic
        pass

    return {
        "name": "test",
        "description": "Test",
        "run": run
    }
"""
        plugin_file.write_text(plugin_content)

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        def mock_chat(messages, model="test", stream=False):
            pass

        result = loader.run_plugin("test", plugins, "test-model", mock_chat)

        assert result is True

    def test_run_plugin_not_found(self, tmp_path):
        """Test running a non-existent plugin"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        loader = PluginLoader(plugins_dir)
        plugins = loader.load_plugins()

        result = loader.run_plugin("nonexistent", plugins, "test-model", lambda: None)

        assert result is False
