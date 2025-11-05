import os
import random
import json
import time
import sys
import threading
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from dotenv import load_dotenv
import data_manager as dm

# --- Logger Utility ---
class Logger:
    @staticmethod
    def warning(msg):
        print(f"\033[93m[WARNING] {msg}\033[0m")
    
    @staticmethod
    def success(msg):
        print(f"\033[92m[SUCCESS] {msg}\033[0m")

# --- Classic Terminal Colors ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ----------------- Setup -----------------
def setup_client():
    """Loads environment variables and logs into Instagram."""
    load_dotenv()
    IG_USERNAME = os.getenv("IG_USERNAME")
    IG_PASSWORD = os.getenv("IG_PASSWORD")
    GROUP_CHAT_ID = os.getenv("IG_GROUP_CHAT_ID")
    SESSION_FILE = "session.json"

    if not all([IG_USERNAME, IG_PASSWORD, GROUP_CHAT_ID]):
        print(f"{Colors.FAIL}Error: Make sure IG_USERNAME, IG_PASSWORD, and IG_GROUP_CHAT_ID are set in the .env file.{Colors.ENDC}")
        sys.exit(1)

    client = Client()
    try:
        if os.path.exists(SESSION_FILE):
            client.load_settings(SESSION_FILE)
            client.login(IG_USERNAME, IG_PASSWORD)
            try:
                # Check if the session is still valid
                client.get_timeline_feed()
            except LoginRequired:
                print(f"{Colors.WARNING}Session expired. Re-logging in...{Colors.ENDC}")
                if os.path.exists(SESSION_FILE):
                    os.remove(SESSION_FILE)
                client.login(IG_USERNAME, IG_PASSWORD, relogin=True)
        else:
            client.login(IG_USERNAME, IG_PASSWORD)
        
        client.dump_settings(SESSION_FILE)
        print(f"{Colors.GREEN}Successfully logged in as {IG_USERNAME}.{Colors.ENDC}")
        return client, IG_USERNAME, int(GROUP_CHAT_ID)
    except Exception as e:
        print(f"{Colors.FAIL}An error occurred during login: {e}{Colors.ENDC}")
        sys.exit(1)

# ----------------- Game State & Cache -----------------
game_state = {
    "trivia": None
}
user_cache = {}
recently_used = {
    "truths": [], "dares": [], "nhies": [],
    "trivia": [], "roasts": []
}

# --- NEW: Rate Limiting and Blocking State ---
user_command_timestamps = {}
blocked_users = {} # Stores { user_id: expiration_timestamp }
# -----------------------------------------------

def get_username(client, user_id):
    """Fetches a username, using a cache to avoid repeated API calls."""
    if not user_id: return "Unknown"
    user_id_str = str(user_id)
    if user_id_str in user_cache:
        return user_cache[user_id_str]
    try:
        user = client.user_info_v1(user_id_str)
        if user:
            username = user.username
            user_cache[user_id_str] = username
            return username
        return user_id_str
    except Exception:
        try:
            user = client.user_info(user_id_str)
            if user:
                username = user.username
                user_cache[user_id_str] = username
                return username
            return user_id_str
        except Exception as e:
            print(f"\r{Colors.WARNING}Could not fetch username for {user_id_str}: {e}{Colors.ENDC}")
            return user_id_str

def get_unique_item(list_name, item_list):
    """
    Gets a unique item from a list that hasn't been used recently.
    Resets the list if all items have been used.
    """
    global recently_used
    if not item_list:
        return None, "No items found in the list!"

    available_indices = [i for i, _ in enumerate(item_list) if i not in recently_used.get(list_name, [])]

    reset_message = None
    if not available_indices:
        recently_used[list_name] = []
        available_indices = list(range(len(item_list)))
        reset_message = "(All questions have been used. Starting over!)"

    chosen_index = random.choice(available_indices)
    recently_used[list_name].append(chosen_index)
    
    return item_list[chosen_index], reset_message


# ----------------- Command Handler -----------------
def handle_command(client, user_id, command, args):
    """Processes bot commands and returns a response."""
    global game_state
    response = ""
    username = get_username(client, user_id)

    # ---- HELP ----
    if command == "!help":
        response = (
            "🤖 Instagram Chat Bot Commands 🤖\n\n"
            "🎉 Fun Commands:\n\n"
            "!truth - Get a truth question.\n"
            "!dare - Get a dare challenge.\n"
            "!nhie - Never Have I Ever question.\n"
            "!roast [@user] - Roast a user or a random member.\n\n"
            "🕹️ Game Commands:\n\n"
            "!trivia - Start a trivia challenge.\n"
            "Fun: \n\n"
            "!pick - Pick a random member from the group.\n"
            "!ship [@user] - Ship a user with a random member.\n"
            "!8ball - Ask the Magic 8-Ball a question.\n\n"
            "Utilities: \n\n"
            "!leaderboard - View the game leaderboard.\n"
            "!setbday <dd-mm> - Set your birthday.\n"
            "!birthdays - View upcoming birthdays.\n\n"
            "Type commands starting with '!' to interact with the bot!\n\n"
            "Coded with love by @linxfaizan"
        )

    # ---- FUN COMMANDS ----
    elif command == "!truth":
        truths = dm.load_list("truths.txt")
        chosen, reset_msg = get_unique_item("truths", truths)
        if not chosen: response = "🚫 No truths found!"
        else:
            response = f"🗣️ Truth for @{username}:\n\n_{chosen}_"
            if reset_msg: response += f"\n\n_{reset_msg}_"

    elif command == "!dare":
        dares = dm.load_list("dares.txt")
        chosen, reset_msg = get_unique_item("dares", dares)
        if not chosen: response = "🚫 No dares found!"
        else:
            response = f"😈 Dare for @{username}:\n\n_{chosen}_"
            if reset_msg: response += f"\n\n_{reset_msg}_"
        
    elif command == "!nhie":
        nhies = dm.load_list("nhie.txt")
        chosen, reset_msg = get_unique_item("nhies", nhies)
        if not chosen: response = "🚫 No NHIE questions found!"
        else:
            response = f"🤫 Never Have I Ever, @{username}...\n\n_{chosen}_"
            if reset_msg: response += f"\n\n_{reset_msg}_"
        
    elif command == "!roast":
        roasts = dm.load_list("roasts.txt")
        roast, reset_msg = get_unique_item("roasts", roasts)
        target_user = f"@{username}"
        if args and args[0].startswith('@'):
            target_user = args[0]
        else:
            try:
                thread = client.direct_thread(str(client.IG_GROUP_CHAT_ID))
                members = [user for user in thread.users if str(user.pk) != str(user_id)]
                if members: target_user = f"@{random.choice(members).username}"
            except Exception: pass
        response = f"🔥 {target_user}, {roast}"
        if reset_msg: response += f"\n\n_{reset_msg}_"
        
    # ---- SOCIAL COMMANDS ----
    elif command == "!pick":
        try:
            thread = client.direct_thread(thread_id=str(client.IG_GROUP_CHAT_ID))
            if not thread.users:
                 response = "Couldn't find any members to pick from!"
            else:
                chosen_one = random.choice(thread.users)
                response = f"🎲 The bot has chosen: @{chosen_one.username}"
        except Exception as e:
            print(f"\r{Colors.FAIL}Error in !pick: {e}{Colors.ENDC}")
            response = "🔮 My crystal ball is cloudy... I can't pick anyone right now."
            
    elif command == "!ship":
        try:
            thread = client.direct_thread(thread_id=str(client.IG_GROUP_CHAT_ID))
            members = thread.users
            if len(members) < 2:
                response = "Not enough members to ship!"
            else:
                user1_name, user2_name = "", ""
                if args and args[0].startswith('@'):
                    user1_name = args[0].lstrip('@')
                    other_members = [m for m in members if m.username.lower() != user1_name.lower()]
                    if other_members:
                        user2_name = random.choice(other_members).username
                    else:
                        response = "Can't ship someone with themselves!"
                else:
                    user1_obj, user2_obj = random.sample(members, 2)
                    user1_name, user2_name = user1_obj.username, user2_obj.username
                
                if user1_name and user2_name:
                    response = f"❤️ Ship: @{user1_name} x @{user2_name} ❤️"
        except Exception as e:
            print(f"\r{Colors.FAIL}Error in !ship: {e}{Colors.ENDC}")
            response = "🚢 The love boat is currently docked due to technical difficulties."


    # ---- GAME COMMANDS ----

    elif command == "!trivia":
        trivia = dm.load_json_from_lists("trivia.json")
        q, reset_msg = get_unique_item("trivia", trivia)
        if not q: response = "🚫 No trivia questions found!"
        else:
            game_state["trivia"] = {"answer": q["answer"].lower(), "user": user_id}
            options = "\n".join([f"*{k.upper()}:* {v}" for k, v in q['options'].items()])
            response = f"🧠 Trivia for @{username}: 🧠\n\n*{q['question']}*\n\n{options}\n\nReply with `!answer <A/B/C/D>`"
            if reset_msg: response += f"\n\n_{reset_msg}_"

    elif command == "!answer" and args:
        ans = " ".join(args).lower()
        if game_state["trivia"]:
            correct = game_state["trivia"]["answer"]
            if ans == correct:
                dm.add_score(str(user_id))
                response = f"✅ Correct, @{username}! The answer was *{correct.upper()}*. (+1 point!)"
                game_state["trivia"] = None
            else:
                response = f"❌ That's not the right option, @{username}! Guess again."
        else:
            response = "❓ No active trivia question!"

    # ---- UTILITY & FUN ----
    elif command == "!skip":
        if game_state["trivia"]:
            correct = game_state["trivia"]["answer"]
            response = f"😕 The trivia has been skipped! The correct option was *{correct.upper()}*."
            game_state["trivia"] = None
        else:
            response = "🤷‍♀️ There's no active game to skip!"

    elif command == "!8ball":
        response = f"🎱 @{username}, the Magic 8-Ball says: *{random.choice(['Yes, definitely.', 'No, certainly not.', 'Perhaps.', 'Ask again later.'])}*"

    elif command == "!leaderboard":
        board = dm.get_leaderboard()
        if not board: response = "🏆 Leaderboard is empty!"
        else:
            leaderboard_lines = [f"🥇 @{get_username(client, board[0][0])}: {board[0][1]}"]
            if len(board) > 1: leaderboard_lines.append(f"🥈 @{get_username(client, board[1][0])}: {board[1][1]}")
            if len(board) > 2: leaderboard_lines.append(f"🥉 @{get_username(client, board[2][0])}: {board[2][1]}")
            for i, (uid, s) in enumerate(board[3:10]):
                leaderboard_lines.append(f"{i+4}. @{get_username(client, uid)}: {s}")
            response = "🏆 *Leaderboard* 🏆\n\n" + "\n".join(leaderboard_lines)

    elif command == "!files":
        files = dm.get_list_file_details()
        response = "📚 *Available Content Lists:*\n" + "\n".join(files)
        
    elif command == "!setbday" and args:
        if len(args[0].split('-')) == 2:
            dm.set_birthday(user_id, args[0])
            response = f"🎂 Birthday for @{username} set to {args[0]}."
        else:
            response = "Please use the format `dd-mm` (e.g., `!setbday 25-12`)."

    elif command == "!birthdays":
        bdays = dm.get_all_birthdays()
        if not bdays: response = "No birthdays have been set yet!"
        else:
            bday_lines = [f"@{get_username(client, uid)}: {d}" for uid, d in bdays.items()]
            response = "🎂 *Upcoming Birthdays* 🎂\n\n" + "\n".join(bday_lines)
            
    elif command == "!exit":
        response = "🤖 Shutting down... Goodbye!"
        # You MUST send the response *before* you exit,
        # or the script will die before the message is sent.
        try:
            client.direct_send(response, thread_ids=[str(client.IG_GROUP_CHAT_ID)])
        except Exception as e:
            print(f"Couldn't send final message: {e}")
        
        # This force-quits the ENTIRE script (both threads)
        os._exit(0)

    # --- Fallback for custom commands ---
    elif command == "!addcmd":
        # Split the message into 3 parts: !addcmd, !new_command, and the rest
        message_text = command + (' ' + ' '.join(args) if args else '')
        parts = message_text.split(' ', 2)            
            # Check if all 3 parts are present
        if len(parts) < 3:
            response = "Usage: !addcmd <!command_name> <response text>"
            Logger.warning(f"Failed !addcmd attempt from @{username} due to incorrect format.")
        else:
            new_cmd = parts[1].lower()
            # Ensure the new command starts with '!'
            if not new_cmd.startswith("!"):
                response = "Command name must start with '!'"
                Logger.warning(f"Failed !addcmd attempt from @{username} because command did not start with '!'.")
            else:
                # Get the response text
                response_text = parts[2]
                # Get existing commands and update
                custom_commands = dm.load_custom_commands()
                custom_commands[new_cmd] = response_text
                # Save the dictionary to the 'custom_commands.json' file
                dm.save_custom_commands(custom_commands)
                response = f"✅ Custom command '{new_cmd}' added!"
                Logger.success(f"Added new custom command '{new_cmd}' from @{username}.")

    else:
        custom_response = dm.get_custom_command(command)
        if custom_response:
            response = custom_response
        else:
            response = f"❓ Unknown command: {command}. Type `!help` for a list of commands."
    return response

# ----------------- Bot Modes -----------------
def listen_to_group(client, group_chat_id):
    """Listens for new messages in the specified group chat and responds."""
    global user_command_timestamps, blocked_users # <-- Make sure we can access the global dicts
    
    print(f"{Colors.CYAN}Listening for messages in group chat ID: {group_chat_id}...{Colors.ENDC}")
    print(f"{Colors.WARNING}Press CTRL+C in the terminal input below to stop the bot.{Colors.ENDC}")
    seen_messages = set()
    
    try:
        thread = client.direct_thread(thread_id=str(group_chat_id), amount=20)
        for message in thread.messages: seen_messages.add(message.id)
        print(f"{Colors.GREEN}Ignoring {len(seen_messages)} pre-existing messages.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}\nCould not fetch initial messages for group chat: {e}{Colors.ENDC}")
        return

    backoff_delay = 60
    max_backoff = 600

    while True:
        try:
            thread = client.direct_thread(thread_id=str(group_chat_id), amount=5)
            if not thread or not thread.messages:
                time.sleep(1)
                continue

            for last_message in reversed(thread.messages):
                if last_message.id in seen_messages: continue
                seen_messages.add(last_message.id)
                
                if last_message.item_type != 'text': continue

                text = last_message.text
                sender_id = str(last_message.user_id) # <-- Use string ID for consistency
                sender_username = get_username(client, sender_id)
                
                # Use \r to move cursor to the beginning of the line to not mess up the input prompt
                print(f"\r{Colors.BLUE}[{sender_username}]: {text}{' ' * 20}{Colors.ENDC}")

                if text and text.startswith("!"):
                    
                    # --- START: NEW RATE LIMITING LOGIC ---
                    current_time = time.time()

                    # 1. Check if user is currently blocked
                    if sender_id in blocked_users:
                        if current_time < blocked_users[sender_id]:
                            # User is still blocked, ignore the command and skip to the next message
                            print(f"\r{Colors.WARNING}Ignoring command from blocked user: @{sender_username}{Colors.ENDC}")
                            continue
                        else:
                            # Block has expired, remove them from the list
                            del blocked_users[sender_id]
                            print(f"\r{Colors.SUCCESS}User @{sender_username} is now unblocked.{Colors.ENDC}")

                    # 2. Track the command timestamp
                    if sender_id not in user_command_timestamps:
                        user_command_timestamps[sender_id] = []
                    
                    # 3. Clean up old timestamps (older than 60 seconds)
                    one_minute_ago = current_time - 60
                    user_command_timestamps[sender_id] = [
                        ts for ts in user_command_timestamps[sender_id] if ts > one_minute_ago
                    ]
                    
                    # 4. Add the new command's timestamp
                    user_command_timestamps[sender_id].append(current_time)
                    
                    # 5. Check if the user has exceeded the limit (7 commands in 60 seconds)
                    if len(user_command_timestamps[sender_id]) > 7:
                        # Block the user for 3 hours (3 * 60 * 60 seconds)
                        block_duration_seconds = 3 * 3600
                        expiration_time = current_time + block_duration_seconds
                        blocked_users[sender_id] = expiration_time
                        
                        # Clear their timestamps so they don't get re-blocked
                        user_command_timestamps[sender_id] = []

                        # Inform the user and log it
                        block_reply = f"@{sender_username} You are sending commands too fast! You have been blocked for 3 hours."
                        client.direct_send(block_reply, thread_ids=[str(group_chat_id)])
                        print(f"\r{Colors.FAIL}Blocking user @{sender_username} for 3 hours.{Colors.ENDC}")
                        
                        # Skip processing their command
                        continue
                    
                    # --- END: NEW RATE LIMITING LOGIC ---

                    # If user is not blocked, proceed as normal
                    parts = text.split()
                    cmd, args = parts[0].lower(), parts[1:]
                    reply = handle_command(client, sender_id, cmd, args)
                    if reply:
                        client.direct_send(reply, thread_ids=[str(group_chat_id)])
                        print(f"\r{Colors.GREEN}[BOT RESPONSE]: {reply.splitlines()[0]}{' ' * 20}{Colors.ENDC}")

            backoff_delay = 60
            time.sleep(1)

        except Exception as e:
            print(f"\r{Colors.FAIL}An error occurred while listening: {e}{Colors.ENDC}")
            print(f"\r{Colors.WARNING}Waiting for {backoff_delay} seconds before retrying...{Colors.ENDC}")
            time.sleep(backoff_delay)
            backoff_delay = min(backoff_delay * 2, max_backoff)

def handle_terminal_input(client, ig_username, group_chat_id):
    """Handles user input from the terminal to send messages."""
    print(f"\n{Colors.CYAN}You can now type messages to send to the group chat.{Colors.ENDC}")
    print(f"Type '{Colors.WARNING}exit{Colors.ENDC}' to quit.")
    
    while True:
        try:
            prompt = f"\r{Colors.CYAN}chatbot@{ig_username} > {Colors.ENDC}"
            text = input(prompt)
            if text.lower() == 'exit':
                break
            if text:
                try:
                    client.direct_send(text, thread_ids=[str(group_chat_id)])
                    print(f"\r{Colors.GREEN}[SENT]: {text}{' ' * 20}{Colors.ENDC}")
                except Exception as e:
                    print(f"\r{Colors.FAIL}Error sending message: {e}{Colors.ENDC}")
        except KeyboardInterrupt:
            break


def main():
    """Main function to start the bot."""
    print(f"""{Colors.GREEN}
        ██████╗  ██████╗ ████████╗
        ██╔══██╗██╔═══██╗╚══██╔══╝
        ██████╔╝██║   ██║   ██║   
        ██╔══██╗██║   ██║   ██║   
        ██████╔╝╚██████╔╝   ██║   
        ╚═════╝  ╚═════╝    ╚═╝   
    {Colors.ENDC}""")
    print(f"{Colors.HEADER}--- Instagram Chat Bot Initializing ---{Colors.ENDC}")
    
    client, ig_username, group_chat_id = setup_client()
    client.IG_GROUP_CHAT_ID = group_chat_id

    # Start the listener in a separate, non-blocking thread
    listener_thread = threading.Thread(
        target=listen_to_group, 
        args=(client, group_chat_id), 
        daemon=True  # This allows the main thread to exit without waiting for this one
    )
    listener_thread.start()

    # The main thread will handle terminal input
    handle_terminal_input(client, ig_username, group_chat_id)
    
    print(f"\n{Colors.HEADER}Bot shutting down. Goodbye!{Colors.ENDC}")

if __name__ == "__main__":
    main()