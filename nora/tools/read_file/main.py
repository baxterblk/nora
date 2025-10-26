import os


def run(params):
    """
    Reads the content of a file.

    Args:
        params: A dictionary of parameters.

    Returns:
        The content of the file or an error message.
    """
    path = params.get("path")

    if not path:
        return "Error: path is a required parameter."

    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"
