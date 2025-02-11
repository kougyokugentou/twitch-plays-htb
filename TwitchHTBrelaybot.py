#!/usr/bin/env python

# TODO: Add !chord command for things like `C-b "` mapping to `ctrl+b "`
# TODO: Make sure !type (and maybe !ctrl) responds to non-letter characters (especially for tmux support)
# TODO: Add !esc for escape ? Or !type esc ?
# TODO: cgroups ???
# TODO: Perhaps consider rewrite for testability/extensibility
#        - Along those lines, consider unit tests
# TODO: Figure out how to many `M-<char>` work (and maybe `H-<char>` while I'm at it...)
# TODO: Version Control

import socket
import pexpect
import os
import threading
import subprocess

# Twitch IRC configuration
server = "irc.chat.twitch.tv"
port = 6667
nickname = "justinfan123"
channel = "#dwangoac"    # Replace with your Twitch channel

# List of privileged users
privileged_users = ["dwangoac", "themas3212"]  # Add usernames here in list "one", "two

# State variables
relay_active = True
bot_pid = os.getpid()  # Get the bot's process ID
bot_pname = subprocess.run(["ps", "-p", str(bot_pid), "-o", "comm="], capture_output=True).stdout.decode('utf-8').rstrip() # Get the bot's process name
pty_shell = None  # Placeholder for the interactive shell
tmux_session = "interactive-twitch" # name of the tmux session

# ANSI Control Character lookup table
escapes = {'^A': '\x01', '^B': '\x02', '^C': '\x03', '^D': '\x04', '^E': '\x05', '^F': '\x06', '^G': '\x07', '^H': '\x08', '^I': '\x09', '^J': '\x0A', '^K': '\x0B', '^L': '\x0C', '^M': '\x0D', '^N': '\x0E', '^O': '\x0F', '^P': '\x10', '^Q': '\x11', '^R': '\x12', '^S': '\x13', '^T': '\x14', '^U': '\x15', '^V': '\x16', '^W': '\x17', '^X': '\x18', '^Y': '\x19', '^Z': '\x1A', '^[': '\x1B', '^\\': '\x1C', '^]': '\x1D', '^^': '\x1E', '^_': '\x1F'}
ESC = escapes['^['] # Escape character for ANSI control sequences
Cc = escapes['^C'] # ANSI character for Ctrl+c
Cb = escapes['^B'] # ANSI chacter for Ctrl+b
# ANSI sequences for cursor control/arrow keys lookup table
arrows = { "up" : f"{ESC}[A", "down": f"{ESC}[B", "right": f"{ESC}[C" , "left":f"{ESC}[C" }

# turns a char into ANSI Ctrl+char character... more or less
# logs and returns empty string if a sinle chracter isn't given
def ctrl(character):
    if len(character) != 1:
        print("only a single character may follow ctrl")
        return ""
    return escapes[f"^{character.upper()}"]

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
    pty_shell = pexpect.spawn("bash --rcfile /etc/bash.bashrc", encoding="utf-8", echo=False, timeout=None)
    subprocess.run(["tmux", "kill-session", "-t", tmux_session])
    pty_shell.sendline(f"tmux new -s {tmux_session}")
    print("Interactive shell initialized.")

def reset_shell():
    #tmux_killer = pexecpt.spawn(f"tmux kill-session -t {tmux-session}")
    #tmux_killer.terminate(True)
    #subprocess.run(["tmux", "kill-session", "-t", tmux_session])
    pty_shell.terminate(True)
    initialize_shell()

def execute_in_shell(command, username, newline=True):
    global pty_shell

    # Block "kill" commands
    command_words = command.lower().strip().split(" ")
    can_kill = command.find("kill") != -1 or command.find("pkill") != -1
    targets_bot = str(bot_pid) in command_words \
        or bot_pname in command_words \
        or str(1) in command_words\
        or command.find(__file__) != -1
    bad_words = command.find("reboot") != -1
    #if command.strip().lower().startswith("kill") and str(bot_pid) in command:
    if bad_words or (can_kill and targets_bot):
        print(f"[{channel}] {username} attempted to use a 'kill' command.")
        print("Please do not try to kill the bot, thank you.")
        return

    try:
        # Send the command to the shell
        print(f"Executing command from {username}: {command}")
        if newline:
            pty_shell.sendline(command)
        else:
            pty_shell.send(command)

        # Read and relay the output line by line
        '''def relay_output():
            while True:
                try:
                    line = pty_shell.readline().strip()
                    if line:
                        print(f"[{channel}] {username}: {line}")
                except pexpect.exceptions.EOF:
                    print("Shell session ended.")
                    break

        threading.Thread(target=relay_output, daemon=True).start()'''
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
                    elif message == "!reset":
                        print(f"Reseting Shell")
                        reset_shell()
                    else:
                        if relay_active and message.startswith("!cmd"):
                            execute_in_shell(message[5:], username)

                # Relay non-privileged messages if active

                def user_action(*args, **kwargs):
                    print(f"[{channel}] {username}: {message}")
                    execute_in_shell(*args, **kwargs)
                
                if relay_active and username not in privileged_users:
                    message_words = message.split(" ")
                    first_word = message_words[0]
                    action = " ".join(message_words[1:])
                    print(f"first_world: {first_word}")
                    match first_word:
                        case "!cmd":
                            user_action(message[5:], username)
                        case "!ctrl":
                            print(f"!ctrl {action}")
                            if len(action)==1 and action.isalpha():
                                user_action(ctrl(action), username, newline=False)
                            else:
                                print("can only use single letters for ctrl")
                        case "!type":
                            print(f"!type {action}")
                            if len(action)==1 and action.isalpha():
                                user_action(action, username, newline=False)
                            elif action.lower() in ['up', 'down', 'left', 'right']:
                                user_action(arrows[action.lower()], username, newline=False)
                            else:
                                print("meant for only typing a single letter, or for arrows keys with up, down, left, or right")
                        case _:
                            continue
        except KeyboardInterrupt:
            print("\nDisconnected from Twitch chat.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break


if __name__ == "__main__":
    try:
        print(f"Connecting to Twitch chat for channel: {channel}...")
        irc = connect_to_twitch()
        initialize_shell()
        print("Connected! Relaying messages:\n")
        relay_chat(irc)
        print("Bot terminated.")
    except Exception as e:
        print(f"Error: {e}")
