#!/usr/bin/env python3
"""
arch-whisper client: Send commands to the arch-whisper daemon.
Called by Hyprland key bindings.
"""

import socket
import sys

SOCKET_PATH = "/tmp/arch-whisper.sock"


def send_command(command: str) -> str:
    """Send a command to the daemon and return the response."""
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(2.0)
        client.connect(SOCKET_PATH)
        client.send(command.encode('utf-8'))
        response = client.recv(1024).decode('utf-8')
        client.close()
        return response
    except FileNotFoundError:
        print("Daemon not running. Start with: systemctl --user start arch-whisper")
        return "error: daemon not running"
    except socket.timeout:
        print("Daemon timeout")
        return "error: timeout"
    except Exception as e:
        print(f"Error: {e}")
        return f"error: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: arch_whisper_client.py <command>")
        print("Commands: start, stop, status, ping")
        sys.exit(1)

    command = sys.argv[1]
    response = send_command(command)
    print(response)


if __name__ == "__main__":
    main()
