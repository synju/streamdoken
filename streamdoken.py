import vlc
import threading
import requests
import time
import sys
import argparse

# ANSI escape codes for controlling terminal output
CLEAR_SCREEN = "\033[2J\033[H"
CLEAR_LINE = "\033[K"
CURSOR_UP = "\033[F"
TITLE_LINE = "# ~~~ [StreamDoken] ~~~ #"


# Function to clear and update the console with title, updates, and command prompt
def update_console(update_message="", prompt_ready=False):
    sys.stdout.write(CLEAR_SCREEN)  # Clear the screen
    sys.stdout.write(f"{TITLE_LINE}\n")  # Always print the title line
    sys.stdout.write(f"Updates: {update_message}\n")  # Update Line 2 with a new message
    if prompt_ready:
        sys.stdout.write(f"$: ")  # Command prompt ready
    sys.stdout.flush()


# Function to log errors to errors.txt
def log_error(message):
    with open("errors.txt", "a") as f:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        f.write(f"{current_time}: {message}\n")


# Function to download and extract the actual stream URL from the .m3u playlist file
def get_stream_url(m3u_url):
    try:
        response = requests.get(m3u_url)
        if response.status_code == 200:
            for line in response.text.splitlines():
                if not line.startswith("#"):  # Skip comment lines
                    return line
        else:
            log_error(f"Failed to retrieve .m3u file, status code: {response.status_code}")
    except Exception as e:
        log_error(f"Error fetching .m3u file: {e}")
    return None


# Function to handle streaming playback
def play_stream(player):
    stream_url = get_stream_url(player['url'])

    if stream_url:
        update_console(f"Playing stream: {stream_url}")
        media = vlc.MediaPlayer(stream_url)
        media.play()

        player['media'] = media  # Store the media object
        time.sleep(2)  # Allow time for the stream to start

        if not media.is_playing():
            update_console("Error: Stream did not start.", prompt_ready=True)
        else:
            update_console("Stream is playing. Awaiting next command...", prompt_ready=True)  # Added here

        # Continue running the stream until stopped
        while not player['stop']:
            time.sleep(1)  # Prevent high CPU usage

        update_console("Stopping stream...", prompt_ready=False)
        media.stop()
        update_console("Stream stopped. Awaiting next command...", prompt_ready=True)
    else:
        update_console("Error: Could not retrieve stream URL from the .m3u file.", prompt_ready=True)


# Function to handle user input commands
def listen_for_commands(player):
    while True:
        # Ensure the console is updated before asking for input
        update_console(prompt_ready=True)  # Set this to True when expecting user input
        command = input().strip().lower()  # Command entry line

        if command == "play":
            if player['media'] is None or not player['media'].is_playing():
                player['stop'] = False
                update_console("Starting stream...", prompt_ready=False)  # Now set to False when stream is starting
                threading.Thread(target=play_stream, args=(player,)).start()
            else:
                update_console("Stream is already playing.", prompt_ready=True)

        elif command == "stop":
            player['stop'] = True
            update_console("Stream stopped by user. Awaiting next command...", prompt_ready=True)

        elif command == "exit":
            update_console("Exiting...", prompt_ready=False)
            player['stop'] = True
            if player['media']:
                player['media'].stop()
            break

        elif command == "clear":
            update_console("", prompt_ready=True)

        elif command == "about":
            update_console("StreamDoken v1.0 by @synjai (x.com)", prompt_ready=True)

        elif command == "help":
            update_console("Available commands: play, stop, exit, clear, about", prompt_ready=True)

        else:
            update_console("Invalid command. Try again.", prompt_ready=True)


# Redirect VLC log output to a file
def vlc_log_redirect():
    instance = vlc.Instance('--quiet')  # --quiet to suppress the default output
    log_file = open("errors.txt", "a")
    sys.stderr = log_file  # Redirect stderr to the log file


# Entry point of the application
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Play an .m3u stream in the terminal.")
    parser.add_argument(
        "m3u_url", nargs="?", default="https://www.bassdrive.com/bassdrive.m3u",
        help="The URL of the .m3u file to play. If not provided, the default Bassdrive URL will be used."
    )

    args = parser.parse_args()  # Parse the arguments

    # Redirect VLC logs to errors.txt
    vlc_log_redirect()

    # Initial clear screen and title print
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(f"{TITLE_LINE}\n")
    update_console("Initializing...", prompt_ready=False)

    # Use the argument provided (or fallback to default)
    stream_m3u_url = args.m3u_url

    # Dictionary to track media player and playback status
    player = {'media': None, 'stop': False, 'url': stream_m3u_url}

    # Start playing the stream automatically
    threading.Thread(target=play_stream, args=(player,)).start()

    # Start the input thread for listening to commands after playback starts
    input_thread = threading.Thread(target=listen_for_commands, args=(player,))
    input_thread.start()

    # Wait for the input thread to finish
    input_thread.join()

    update_console("Application closed.", prompt_ready=False)
