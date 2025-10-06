"""
NORA Utilities

Colored terminal output and logging configuration utilities.
"""

import logging
import sys
from typing import Optional


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def colored(text: str, color: str, bold: bool = False) -> str:
    """
    Return colored text for terminal output.

    Args:
        text: Text to colorize
        color: Color code from Colors class
        bold: Whether to make text bold

    Returns:
        Formatted string with ANSI color codes
    """
    prefix = Colors.BOLD if bold else ""
    return f"{prefix}{color}{text}{Colors.RESET}"


def success(message: str) -> None:
    """Print a success message in green."""
    print(colored(f"✓ {message}", Colors.GREEN, bold=True))


def warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(colored(f"⚠ {message}", Colors.YELLOW, bold=True))


def error(message: str) -> None:
    """Print an error message in red."""
    print(colored(f"✗ {message}", Colors.RED, bold=True))


def info(message: str) -> None:
    """Print an info message in cyan."""
    print(colored(f"ℹ {message}", Colors.CYAN))


def banner(message: str) -> None:
    """Print a banner message in blue."""
    print(colored(f"\n{'=' * 60}", Colors.BLUE))
    print(colored(message.center(60), Colors.BLUE, bold=True))
    print(colored(f"{'=' * 60}\n", Colors.BLUE))


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure logging for NORA.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    root_logger.handlers = []

    # Console handler (only for WARNING and above by default)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def connection_banner(url: str, model: str, status: str = "Connected") -> None:
    """
    Display a connection status banner.

    Args:
        url: Ollama API URL
        model: Model name
        status: Connection status
    """
    status_color = Colors.GREEN if status == "Connected" else Colors.RED
    print(colored("─" * 70, Colors.BLUE))
    print(
        colored("NORA", Colors.CYAN, bold=True) + " | " +
        colored(f"{status}", status_color, bold=True) + " | " +
        colored(f"{url}", Colors.WHITE) + " | " +
        colored(f"Model: {model}", Colors.YELLOW)
    )
    print(colored("─" * 70, Colors.BLUE))
