import json
import os
from datetime import datetime

# --- File Paths ---
LISTS_DIR = "lists"
DATA_DIR = "data"
SCORES_FILE = os.path.join(DATA_DIR, "scores.json")
BIRTHDAYS_FILE = os.path.join(DATA_DIR, "birthdays.json")
CUSTOM_COMMANDS_FILE = os.path.join(DATA_DIR, "custom_commands.json")

# --- Ensure directories exist ---
os.makedirs(LISTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# --- Generic JSON Handlers ---

def load_json(filepath, default_value):
    """Loads data from a JSON file."""
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_value
    except Exception as e:
        print(f"Error loading JSON from {filepath}: {e}")
        return default_value

def save_json(filepath, data):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")

# --- List Functions ---

def load_list(filename):
    """Loads a list of items from a text file in the 'lists' directory."""
    filepath = os.path.join(LISTS_DIR, filename)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading list {filename}: {e}")
        return []

def load_json_from_lists(filename):
    """Loads a JSON file from the 'lists' directory."""
    filepath = os.path.join(LISTS_DIR, filename)
    return load_json(filepath, [])

def get_list_file_details():
    """Gets the names and line counts of files in the 'lists' directory."""
    files_details = []
    try:
        for filename in os.listdir(LISTS_DIR):
            filepath = os.path.join(LISTS_DIR, filename)
            count = 0
            if filename.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    count = len([line for line in f if line.strip()])
                files_details.append(f"• {filename} ({count} items)")
            elif filename.endswith('.json'):
                data = load_json(filepath, [])
                count = len(data)
                files_details.append(f"• {filename} ({count} items)")
    except Exception as e:
        print(f"Error getting file details: {e}")
    return files_details

# --- Score Functions ---

def load_scores():
    """Loads the scores dictionary from scores.json."""
    return load_json(SCORES_FILE, {})

def add_score(user_id, points=1):
    """Adds points to a user's score."""
    scores = load_scores()
    user_id = str(user_id)
    if user_id not in scores:
        scores[user_id] = 0
    scores[user_id] += points
    save_json(SCORES_FILE, scores)

def get_leaderboard():
    """Gets the scores, sorted from highest to lowest."""
    scores = load_scores()
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_scores

# --- Birthday Functions ---

def load_birthdays():
    """Loads the birthdays dictionary from birthdays.json."""
    return load_json(BIRTHDAYS_FILE, {})

def set_birthday(user_id, bday_str):
    """Saves a user's birthday."""
    birthdays = load_birthdays()
    birthdays[str(user_id)] = bday_str
    save_json(BIRTHDAYS_FILE, birthdays)

def get_all_birthdays():
    """Gets all saved birthdays, sorted by date."""
    birthdays = load_birthdays()
    try:
        # Sort by month and day
        sorted_bdays = sorted(birthdays.items(), key=lambda item: datetime.strptime(item[1], '%d-%m').strftime('%m-%d'))
        return dict(sorted_bdays)
    except Exception as e:
        print(f"Error sorting birthdays: {e}")
        return birthdays # Return unsorted if an error occurs

# --- Custom Command Functions ---

def load_custom_commands():
    """Loads the custom commands dictionary from custom_commands.json."""
    return load_json(CUSTOM_COMMANDS_FILE, {})

def save_custom_commands(commands_data):
    """Saves the custom commands dictionary to custom_commands.json."""
    save_json(CUSTOM_COMMANDS_FILE, commands_data)

def get_custom_command(command):
    """
    Loads all custom commands and returns the response for a specific command.
    This is the missing function your bot.py file needs.
    """
    commands = load_custom_commands()
    return commands.get(command)

