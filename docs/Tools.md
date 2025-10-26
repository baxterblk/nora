# NORA Tool Specification

NORA's tool system allows for the creation of custom tools that can be used by agents to perform a variety of tasks. Each tool is defined by a manifest file and a Python script.

## Tool Manifest

The tool manifest is a JSON file that describes the tool and its parameters. The manifest must be named `tool.json` and be located in the root directory of the tool.

### Manifest Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NORA Tool Manifest",
  "description": "A manifest for a NORA tool.",
  "type": "object",
  "required": [
    "name",
    "description",
    "entrypoint",
    "parameters"
  ],
  "properties": {
    "name": {
      "description": "The name of the tool.",
      "type": "string"
    },
    "description": {
      "description": "A brief description of what the tool does.",
      "type": "string"
    },
    "entrypoint": {
      "description": "The name of the Python script to execute.",
      "type": "string"
    },
    "parameters": {
      "description": "The parameters that the tool accepts.",
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["object"]
        },
        "properties": {
          "type": "object",
          "patternProperties": {
            "^[a-zA-Z0-9_]+$": {
              "type": "object",
              "properties": {
                "type": {
                  "type": "string"
                },
                "description": {
                  "type": "string"
                },
                "required": {
                  "type": "boolean"
                }
              },
              "required": ["type", "description", "required"]
            }
          }
        }
      }
    }
  }
}
```

### Example Manifest

Here is an example of a `tool.json` file for a tool that reads a file:

```json
{
  "name": "file_reader",
  "description": "Reads the content of a file.",
  "entrypoint": "main.py",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "The path to the file to read.",
        "required": true
      }
    }
  }
}
```

## Tool Script

The tool script is a Python script that contains the logic for the tool. The script must contain a `run` function that takes a dictionary of parameters as input and returns a string as output.

### Example Script

Here is an example of a `main.py` file for the `file_reader` tool:

```python
def run(params):
  """
  Reads the content of a file.

  Args:
    params: A dictionary of parameters.

  Returns:
    The content of the file.
  """
  with open(params["path"], "r") as f:
    return f.read()
```
