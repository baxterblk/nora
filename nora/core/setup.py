"""
NORA First-Run Setup Wizard

Interactive configuration wizard for first-time NORA users.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests  # type: ignore

from . import utils
from .config import DEFAULT_CONFIG, ConfigManager

logger = logging.getLogger(__name__)


def check_ollama_connection(url: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Test connection to Ollama API.

    Args:
        url: Ollama API URL to test

    Returns:
        Tuple of (success: bool, response: dict or None)
    """
    try:
        r = requests.get(f"{url}/api/version", timeout=5, verify=False)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        logger.error(f"Connection failed to {url}: {e}")
        return False, None


def get_available_models(url: str) -> list[str]:
    """
    Get list of available models from Ollama.

    Args:
        url: Ollama API URL

    Returns:
        List of model names
    """
    try:
        r = requests.get(f"{url}/api/tags", timeout=5, verify=False)
        r.raise_for_status()
        data = r.json()
        models = [model["name"] for model in data.get("models", [])]
        return models
    except Exception as e:
        logger.error(f"Failed to get models from {url}: {e}")
        return []


def first_run_wizard() -> Dict[str, Any]:
    """
    Interactive setup wizard for first-time NORA users.

    Returns:
        Configuration dictionary to save
    """
    print("\n" + "=" * 70)
    print("Welcome to NORA! 🤖")
    print("Let's set up your configuration.")
    print("=" * 70 + "\n")

    # Step 1: Get Ollama URL
    utils.info("Step 1: Ollama Connection")
    print(f"Default Ollama URL: {DEFAULT_CONFIG['ollama']['url']}")

    url = None
    while url is None:
        user_input = input(f"Ollama URL [{DEFAULT_CONFIG['ollama']['url']}]: ").strip()
        test_url = user_input or DEFAULT_CONFIG["ollama"]["url"]

        utils.info(f"Testing connection to {test_url}...")
        success, response = check_ollama_connection(test_url)

        if success and response:
            utils.success(
                f"✓ Connected! Ollama version: {response.get('version', 'unknown')}"
            )
            url = test_url
        else:
            utils.error("✗ Connection failed!")
            print("\nPossible issues:")
            print("  - Ollama is not running (try: ollama serve)")
            print("  - Wrong URL or port")
            print("  - Firewall blocking connection")
            retry = input("\nRetry? [Y/n]: ").strip().lower()
            if retry == "n":
                utils.warning("Using default URL anyway. You can change it later with:")
                utils.info("  nora config set ollama.url <your-url>")
                url = test_url
                break

    # Step 2: Check for available models
    print("\n" + "-" * 70)
    utils.info("Step 2: Model Selection")

    models = get_available_models(url)

    if not models:
        utils.warning("No models found on Ollama server.")
        print(f"Default model: {DEFAULT_CONFIG['model']}")
        print("\nTo use NORA, you'll need to pull a model first:")
        print(f"  ollama pull {DEFAULT_CONFIG['model']}")
        model = DEFAULT_CONFIG["model"]
    else:
        utils.success(f"✓ Found {len(models)} model(s):")
        for i, model_name in enumerate(models, 1):
            print(f"  {i}. {model_name}")

        while True:
            try:
                selection = input(f"\nSelect a model (1-{len(models)}) [1]: ").strip()
                if not selection:
                    model = models[0]
                    break

                selection_index = int(selection) - 1
                if 0 <= selection_index < len(models):
                    model = models[selection_index]
                    break
                else:
                    utils.error(
                        f"Invalid selection. Please enter a number between 1 and {len(models)}."
                    )
            except ValueError:
                utils.error("Invalid input. Please enter a number.")

    # Step 3: Create configuration
    config = {
        "model": model,
        "ollama": {"url": url, "verify_ssl": False},
        "profiles": {},
    }

    # Step 4: Save configuration
    print("\n" + "-" * 70)
    utils.info("Step 3: Saving Configuration")

    config_manager = ConfigManager()
    config_manager.config = config
    config_manager.save()

    utils.success(f"✓ Configuration saved to {config_manager.path}")
    print("\n" + "=" * 70)
    print("Setup complete! 🎉")
    print("\nGet started:")
    print("  nora chat              # Start an interactive chat")
    print('  nora run "<prompt>"    # Run a one-shot prompt')
    print("  nora agents            # List available agents")
    print("=" * 70 + "\n")

    return config


def should_run_wizard() -> bool:
    """
    Determine if the setup wizard should run.

    Returns:
        True if wizard should run, False otherwise
    """
    # Check if NORA_CI environment variable is set
    if os.environ.get("NORA_CI", "").lower() == "true":
        logger.debug("Skipping wizard: NORA_CI=true")
        return False

    # Check if config file already exists
    config_manager = ConfigManager()
    if config_manager.path.exists():
        logger.debug(f"Skipping wizard: config exists at {config_manager.path}")
        return False

    return True
