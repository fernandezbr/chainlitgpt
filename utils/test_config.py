import json
import os

# Path to the sample LLM config file
config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'llm_config/llm_config.json')

try:
    # Read JSON data from file
    with open(config_file_path, 'r', encoding='utf-8') as file:
        config_data = json.load(file)
    
    # Print the formatted JSON data
    print(json.dumps(config_data))

except FileNotFoundError:
    print(f"Error: Could not find the config file at {config_file_path}")
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON format in config file - {e}")
except Exception as e:
    print(f"Error: An unexpected error occurred - {e}")
