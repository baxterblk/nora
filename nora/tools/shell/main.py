import subprocess


def run(params):
    """
    Executes a shell command.

    Args:
        params: A dictionary of parameters.

    Returns:
        The output of the command or an error message.
    """
    command = params.get("command")

    if not command:
        return "Error: command is a required parameter."

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr
    except Exception as e:
        return f"Error executing command: {e}"
