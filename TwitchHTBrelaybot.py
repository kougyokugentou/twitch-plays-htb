import socket
import pexpect
import os
import threading

# Twitch IRC configuration
server = "irc.chat.twitch.tv"
port = 6667
nickname = "justinfan123"
channel = "#kougyoku_gentou"    # Replace with your Twitch channel

# List of privileged users
privileged_users = ["kougyoku_gentou"]  # Add usernames here in list "one", "two

# State variables
relay_active = True
bot_pid = os.getpid()  # Get the bot's process ID
pty_shell = None  # Placeholder for the interactive shell


def connect_to_twitch():
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((server, port))

    # Send authentication information
    irc.send(f"NICK {nickname}\r\n".encode("utf-8"))

    # Join the channel
    irc.send(f"JOIN {channel}\r\n".encode("utf-8"))
    print(f"Joined channel: {channel}")

    return irc


def initialize_shell():
    global pty_shell

    # Start a bash shell in a PTY with timeout disabled
    pty_shell = pexpect.spawn("bash", encoding="utf-8", echo=False, timeout=None)
    print("Interactive shell initialized.")


def execute_in_shell(command, username):
    global pty_shell

    # Block "kill" commands
    if command.strip().lower().startswith("kill") and str(bot_pid) in command:
        print(f"[{channel}] {username} attempted to use a 'kill' command.")
        print("Please do not try to kill the bot, thank you.")
        return

    try:
        # Send the command to the shell
        print(f"Executing command from {username}: {command}")
        pty_shell.sendline(command)

        # Read and relay the output line by line
        def relay_output():
            while True:
                try:
                    line = pty_shell.readline().strip()
                    if line:
                        print(f"[{channel}] {username}: {line}")
                except pexpect.exceptions.EOF:
                    print("Shell session ended.")
                    break

        threading.Thread(target=relay_output, daemon=True).start()
    except Exception as e:
        print(f"Error executing command: {e}")


def relay_chat(irc):
    global relay_active

    while True:
        try:
            response = irc.recv(2048).decode("utf-8")

            if response.startswith("PING"):
                irc.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            elif "PRIVMSG" in response:
                # Parse chat messages
                username = response.split("!", 1)[0][1:]
                message = response.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()

                # Privileged user commands
                if username in privileged_users:
                    if message == "!start":
                        relay_active = True
                        print(f"Relay started in {channel}.")
                    elif message == "!stop":
                        relay_active = False
                        print(f"Relay stopped in {channel}.")
                    elif message == "!exit":
                        print(f"Exiting bot as per privileged user command.")
                        break
                    else:
                        if relay_active:
                            execute_in_shell(message, username)

                # Relay non-privileged messages if active
                if relay_active and username not in privileged_users:
                    print(f"[{channel}] {username}: {message}")
        except KeyboardInterrupt:
            print("\nDisconnected from Twitch chat.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break


if __name__ == "__main__":
    print(f"Connecting to Twitch chat for channel: {channel}...")
    irc = connect_to_twitch()
    initialize_shell()
    print("Connected! Relaying messages:\n")
    relay_chat(irc)
    print("Bot terminated.")
