import os


def run(params):
    """
    Appends content to an existing file.

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
        with open(path, "a") as f:
            f.write(content)
        return f"Successfully appended to file: {path}"
    except Exception as e:
        return f"Error appending to file: {e}"
