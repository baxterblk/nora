import os


def run(params):
    """
    Creates a new file with the given content.

    Args:
        params: A dictionary of parameters.

    Returns:
        A message indicating success or failure.
    """
    path = params.get("path")
    content = params.get("content")

    if not path or not content:
        return "Error: path and content are required parameters."

    try:
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully created file: {path}"
    except Exception as e:
        return f"Error creating file: {e}"
