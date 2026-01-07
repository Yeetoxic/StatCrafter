from flask import Flask, render_template, jsonify
import json
import os
from PlayerGrabber import PlayerGrabber
from MinecraftStatsHandler import MinecraftStatsHandler
from advancement_criteria_generator import build_multi_part_advancements
import threading
import time
from datetime import datetime
from mcstatus import JavaServer
import nbtlib
import logging
import socket

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

STATS_DIR = os.path.join(BASE_DIR, 'output_data', 'simplified_stats')

DATA_FILE_PATH = os.path.join(BASE_DIR, 'output_data', 'usernames.json')

SERVER_ADDRESS = "localhost"

FILE_PATH = "../logs/latest.log"

# Create a threading event to signal when to stop
stop_event = threading.Event()

# Suppress Werkzeug logs
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Get the local IP address
my_ip = socket.gethostbyname(socket.gethostname())

def find_latest_jar(versions_dir="./versions"):
    # List all subdirectories
    subdirs = [d for d in os.listdir(versions_dir)
               if os.path.isdir(os.path.join(versions_dir, d))]

    if not subdirs:
        raise FileNotFoundError(f"No version folders found in {versions_dir}")

    # Sort directories in reverse (latest first)
    latest_version = sorted(subdirs, reverse=True)[0]
    latest_folder = os.path.join(versions_dir, latest_version)

    # Look for any file starting with 'server-' and ending with '.jar'
    for f in os.listdir(latest_folder):
        if f.startswith("server-") and f.endswith(".jar"):
            return os.path.join(latest_folder, f)

    raise FileNotFoundError(f"No server-*.jar found in {latest_folder}")

def run_initial_processing():
    global stop_event
    """
    Runs PlayerGrabber and MinecraftStatsHandler to process data when the app starts.
    """
    print("Starting initial data processing...")
    
    build_multi_part_advancements(find_latest_jar("../versions"), "static/advancement_criteria.json")

    # Process player data using PlayerGrabber
    input_folder = "../world/playerdata"
    output_folder = "./output_data/playerdata"
    os.makedirs(output_folder, exist_ok=True)
    while not stop_event.is_set():
        try:
            for file in os.listdir(input_folder):
                if file.endswith(".dat"):
                    input_file = os.path.join(input_folder, file)
                    output_file = os.path.join(output_folder, f"{file.split('.')[0]}.json")
                    grabber = PlayerGrabber(input_file, output_file)
                    grabber.process_data()

            # Process stats and advancements using MinecraftStatsHandler
            try:
                dummy = MinecraftStatsHandler("dummy_uuid")
                for player_uuid in dummy.folder:
                    try:
                        player = MinecraftStatsHandler(player_uuid)
                        result = player.get_minecraft_usernames()
                        if isinstance(result, dict) and "name" in result:
                            # print(f"Username: {result['name']}")
                            player.get_minecraft_skins()

                            # Grab cape from capes.dev
                            player.get_minecraft_capes()

                            # Generate advancement report
                            player.generate_achievement_report()

                            # Convert stats to simplified JSON
                            player.convert_stats_to_simplified_json()
                            #print("")
                        else:
                            #print(result)
                            pass
                    except Exception as e:
                        print(f"An error occurred with UUID {player_uuid}: {e}")
                dummy.write_playerdata()
            except Exception as main_e:
                print(f"An error occurred in the main execution: {main_e}")
            # Sleep between cycles if no stop event is set
            if not stop_event.is_set():
                time.sleep(5)
        except Exception as e:
            print(f"An error occurred during data processing: {e}")
            break  # In case of an unexpected error, exit the loop gracefully
    print("Initial data processing complete.")


# Load data from JSON
def load_data():
    with open(DATA_FILE_PATH, 'r') as f:
        data = json.load(f)
    
    # Convert the "usermap" dictionary into a list of player dictionaries
    players = [{"uuid": uuid, "username": username} for uuid, username in data["usermap"].items()]
    
    return players

def load_player_stats(uuid):
    stats_file = os.path.join(STATS_DIR, f"simplified_stats_{uuid}.json")
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            return json.load(f)
    return None

def load_advancements(player_uuid):
    advancements_file_path = os.path.join(BASE_DIR, 'output_data/advancements_reports', f'advancements_report_{player_uuid}.json')
    try:
        with open(advancements_file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


with open('StatCrafterConfig.json') as config_file:
    config_data = json.load(config_file)

    
# Server Clock
def calculate_uptime():
    """Calculate and return the server's uptime as a string."""
    try:
        if not os.path.exists(FILE_PATH):
            return "Log file not found."

        server_start_time = None
        server_stop_time = None

        with open(FILE_PATH, "r") as log_file:
            lines = log_file.readlines()

        # Get today's date to associate with timestamps
        today_date = datetime.now().date()

        for line in lines:
            if "Starting minecraft server" in line:
                # Extract the timestamp and parse it
                timestamp_str = line.split("]")[0].strip("[")  # Extracts HH:MM:SS
                start_time = datetime.strptime(timestamp_str, "%H:%M:%S").time()
                server_start_time = datetime.combine(today_date, start_time)
                server_stop_time = None  # Reset stop time if server restarts
            elif "Stopping server" in line:
                # Extract the timestamp and parse it
                timestamp_str = line.split("]")[0].strip("[")
                stop_time = datetime.strptime(timestamp_str, "%H:%M:%S").time()
                server_stop_time = datetime.combine(today_date, stop_time)

        if server_start_time:
            if server_stop_time:
                uptime = server_stop_time - server_start_time
            else:
                # If the server is running, calculate uptime until now
                current_time = datetime.now()
                uptime = current_time - server_start_time

            # Format uptime as days, hours, minutes, and seconds
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f'{days} Days, {hours:02}:{minutes:02}:{seconds:02}'

        return "No start event found in the logs."
    except Exception as e:
        return f"Error: {e}"

@app.route("/uptime", methods=["GET"])
def get_uptime():
    """API endpoint to get the server's uptime."""
    uptime = calculate_uptime()
    return jsonify({"uptime": uptime})


# Player Counter
@app.route('/live_player_count', methods=['GET'])
def live_player_count():
    """Fetch the current player count from the Minecraft server."""
    try:
        server = JavaServer(SERVER_ADDRESS, 25565)
        status = server.status()
        #print(f"Players online: {status.players.online}, Max players: {status.players.max}")
        return jsonify({
            "online_players": status.players.online,
            "max_players": status.players.max
        })
    except Exception as e:
        print(f"Error fetching player count: {e}")  # Log detailed error
        return jsonify({
            "error": "Could not retrieve player count",
            "details": str(e)
        }), 500



def get_active_players_using_mcstatus():
    """
    Uses mcstatus to fetch the currently active players on the Minecraft server.
    Returns a set of active player names or an error message if the server is unreachable.
    """
    try:
        # Query the Minecraft server
        server = JavaServer(SERVER_ADDRESS, 25565)
        status = server.status()

        # Extract the list of player names
        if status.players.sample:
            active_players = {player.name for player in status.players.sample}
        else:
            active_players = set()

        return active_players
    except Exception as e:
        print(f"Error querying server for active players: {e}")
        return set()




# Get Game Version
def get_minecraft_version(level_dat_path):
    try:
        # Load the level.dat file
        level_data = nbtlib.load(level_dat_path)

        # Look for the "Version" field
        if 'Version' in level_data['Data']:
            version_data = level_data['Data']['Version']
            version_name = version_data.get('Name', 'Unknown')
            return f"{version_name}"
        else:
            return "Version information not found in level.dat."
    except Exception as e:
        return f"Error reading level.dat: {e}"



# Get online players!
@app.route('/online_players', methods=['GET'])
def online_players():
    """Fetch the list of online players and their pings."""
    try:
        # Parse active players using mcstatus
        active_players = get_active_players_using_mcstatus()
        #print(f"Active players: {active_players}")  # Debugging

        # Return the data in JSON format
        return jsonify({
            "players": sorted(list(active_players)),  # Sort for consistency
        })
    except Exception as e:
        error_message = f"Could not retrieve online players. Error: {e}"
        print(error_message)
        return jsonify({
            "error": "Could not retrieve online players",
            "details": error_message
        }), 500


























@app.route('/')
def index():
    level_dat_path = os.path.join("../world/", "level.dat")
    minecraft_version = get_minecraft_version(level_dat_path)
    players = load_data()
    return render_template('index.html', players=players, minecraft_version=minecraft_version, config=config_data)

# @app.route('/output_data')
# def output_data():
#     pass

@app.route('/player/<uuid>')
def player_page(uuid):
    players = load_data()
    player = next((p for p in players if p["uuid"] == uuid), None)
    if not player:
        return "Player not found", 404
    
    stats = None
    try:
        stats = load_player_stats(uuid)
    except FileNotFoundError:
        stats = None
        
    if stats is None:
        stats = {
            "minecraft:custom": {
                "minecraft:play_time": 100,
                "minecraft:jump": 0,
                "minecraft:walk_one_cm": 0,
                "minecraft:fly_one_cm": 0
            }
        }
        print(f"Stats file not found for {uuid}, using default.")
    
    advancements = load_advancements(uuid)
    return render_template('player.html', player=player, stats=stats, advancements=advancements, config=config_data)

@app.route('/player/<uuid>/advancements')
def player_advancements(uuid):
    players = load_data()
    player = next((p for p in players if p["uuid"] == uuid), None)
    if not player:
        return "Player not found", 404
    
    # Load the advancements for the player
    advancements = load_advancements(uuid) or {"multi_part_advancements": {}}
    
    return render_template('advancements.html', player=player, advancements=advancements, config=config_data)


if __name__ == "__main__":
    # Run initial data processing
    processing_thread = threading.Thread(target=run_initial_processing)
    processing_thread.start()
    # Start the Flask app
    try:
        # Run the Flask app on the main thread
        print("Flask app starting...")
        print(f"Server is running on http://127.0.0.1:5000 or http://{my_ip}:5000")
        app.run(debug=False, host='0.0.0.0')
    except KeyboardInterrupt:
        pass
        # Handle ^C (Ctrl+C) gracefully
    print("Received KeyboardInterrupt, stopping Flask app.")
    stop_event.set()  # Set the event to signal the thread to stop
    # Ensure the background thread finishes before the program exits
    processing_thread.join()
    print("Background processing complete, shutting down.")