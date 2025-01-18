import socket
import subprocess

# Twitch IRC configuration
server = "irc.chat.twitch.tv"
port = 6667
nickname = "justinfan123"
channel = "#kougyoku_gentou"  # Replace with your Twitch channel name

# List of privileged users
privileged_users = ["kougyoku_gentou"]  # Add usernames here in the list: "one","two"

# State variables
relay_active = True

def connect_to_twitch():
    # Create a socket connection
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server, port))

    # Send authentication information
    irc.send(f"NICK {nickname}\r\n".encode("utf-8"))
    irc.send(f"JOIN {channel}\r\n".encode("utf-8"))

    return irc

def execute_bash_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"Command Output:\n{result.stdout}")
        if result.stderr:
            print(f"Command Error:\n{result.stderr}")
    except Exception as e:
        print(f"Error executing command: {e}")

def relay_chat(irc):
    global relay_active

    while True:
        try:
            response = irc.recv(2048).decode("utf-8")

            if response.startswith("PING"):
                # Respond to PINGs to keep the connection alive
                irc.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            elif "PRIVMSG" in response:
                # Parse chat messages
                username = response.split("!", 1)[0][1:]
                message = response.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()

                # Privileged user commands
                if username in privileged_users:
                    if message == "!start":
                        relay_active = True
                        print("Relay started.")
                    elif message == "!stop":
                        relay_active = False
                        print("Relay stopped.")
                    elif message == "!exit":
                        print("Exiting bot as per privileged user command.")
                        break
                    else:
                        if relay_active:
                            print(f"Executing command from {username}: {message}")
                            execute_bash_command(message)

                # Relay non-privileged messages if active
                if relay_active and username not in privileged_users:
                    print(f"{username}: {message}")
        except KeyboardInterrupt:
            print("\nDisconnected from Twitch chat.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    print(f"Connecting to {channel} Twitch chat...")
    irc = connect_to_twitch()
    print("Connected! Relaying messages:\n")
    relay_chat(irc)
    print("Bot terminated.")
