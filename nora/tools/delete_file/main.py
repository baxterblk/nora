import os


def run(params):
    """
    Deletes a file.

    Args:
        params: A dictionary of parameters.

    Returns:
        A message indicating success or failure.
    """
    path = params.get("path")

    if not path:
        return "Error: path is a required parameter."

    try:
        os.remove(path)
        return f"Successfully deleted file: {path}"
    except Exception as e:
        return f"Error deleting file: {e}"
