#!/usr/bin/env python3
"""
PiTunnel Manager - A terminal-based configurator for managing PiTunnel connections
"""

import os
import subprocess
import re
import sys
import time

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_running_pitunnels():
    """Get list of running pitunnel processes."""
    try:
        # Get running processes containing "pitunnel"
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        processes = []
        for line in result.stdout.splitlines():
            if "pitunnel" in line and not "pitunnel_manager.py" in line:
                processes.append(line)
        
        # Parse the process information
        parsed_processes = []
        for process in processes:
            parts = process.split(None, 10)
            if len(parts) >= 11:
                pid = parts[1]
                cmd = parts[10]
                
                # Extract port number
                port_match = re.search(r'--port=(\d+)', cmd)
                port = port_match.group(1) if port_match else "Unknown"
                
                # Extract tunnel name if available
                name_match = re.search(r'--name=([^ ]+)', cmd)
                name = name_match.group(1) if name_match else "Unnamed"
                
                # Extract tunnel type
                tunnel_type = "HTTP" if "--http" in cmd else "Custom"
                
                parsed_processes.append({
                    "pid": pid,
                    "port": port,
                    "name": name,
                    "type": tunnel_type,
                    "command": cmd
                })
        
        return parsed_processes
    except subprocess.SubprocessError as e:
        print(f"Error getting processes: {e}")
        return []

def display_running_tunnels():
    """Display currently running pitunnel processes."""
    processes = get_running_pitunnels()
    
    if not processes:
        print("\nNo active PiTunnel processes found.")
        return processes
    
    print("\nActive PiTunnel Processes:")
    print("-" * 80)
    print(f"{'#':<3} {'PID':<8} {'Port':<6} {'Type':<7} {'Name':<20} {'Command'}")
    print("-" * 80)
    
    for i, proc in enumerate(processes, 1):
        print(f"{i:<3} {proc['pid']:<8} {proc['port']:<6} {proc['type']:<7} {proc['name']:<20} {proc['command'][:40]}...")
    
    return processes

def create_tunnel():
    """Create a new pitunnel."""
    print("\nCreate a new PiTunnel")
    print("-" * 40)
    
    # Get port number
    while True:
        port = input("Local port to expose: ")
        if port.isdigit():
            break
        print("Please enter a valid port number.")
    
    # Get tunnel type
    print("\nTunnel Type:")
    print("1. HTTP (default)")
    print("2. Custom")
    tunnel_type = input("Select tunnel type [1]: ").strip() or "1"
    
    # Get tunnel name (optional)
    name = input("\nTunnel name (subdomain) [optional]: ").strip()
    
    # Ask if tunnel should be persistent
    persistent = input("\nMake tunnel persistent? (y/n) [n]: ").lower().startswith('y')
    
    # Build the command
    command = ["pitunnel", f"--port={port}"]
    
    if tunnel_type == "1":
        command.append("--http")
    
    if name:
        command.append(f"--name={name}")
    
    if persistent:
        command.append("--persist")
    
    # Confirm with user
    print("\nCommand to execute:")
    print(" ".join(command))
    confirm = input("\nCreate tunnel? (y/n): ").lower()
    
    if confirm.startswith('y'):
        try:
            subprocess.Popen(command)
            print("\nTunnel created successfully!")
            time.sleep(2)  # Give time to see the message
        except Exception as e:
            print(f"\nError creating tunnel: {e}")
            input("Press Enter to continue...")
    else:
        print("\nTunnel creation cancelled.")
        time.sleep(1)

def get_persistent_tunnels():
    """Get list of persistent tunnels configured in PiTunnel."""
    try:
        # Get list of persistent tunnels using pitunnel --list
        result = subprocess.run(
            ["pitunnel", "--list"],
            capture_output=True,
            text=True,
            check=True
        )
        
        persistent_tunnels = []
        lines = result.stdout.strip().splitlines()
        
        # Find the table in the output
        table_start = False
        for line in lines:
            if '| ID |' in line:
                table_start = True
                continue
            if table_start and line.startswith('+----+'):
                continue
            if table_start and '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    tunnel_id = parts[1].strip()
                    args = parts[2].strip()
                    persistent_tunnels.append({
                        "id": tunnel_id,
                        "args": args
                    })
        
        return persistent_tunnels
    except subprocess.SubprocessError as e:
        print(f"Error getting persistent tunnels: {e}")
        return []

def remove_tunnel(processes):
    """Remove a running pitunnel process."""
    if not processes:
        print("\nNo active tunnels to remove.")
        input("Press Enter to continue...")
        return
    
    # Get persistent tunnels
    persistent_tunnels = get_persistent_tunnels()
    
    while True:
        choice = input("\nEnter the number of the tunnel to remove (or 0 to cancel): ")
        if choice == "0":
            return
        
        try:
            choice = int(choice)
            if 1 <= choice <= len(processes):
                process = processes[choice-1]
                pid = process["pid"]
                port = process["port"]
                name = process["name"]
                
                # Check if this is a persistent tunnel
                is_persistent = False
                persistent_id = None
                for tunnel in persistent_tunnels:
                    if (f"--port={port}" in tunnel["args"]) and (f"--name={name}" in tunnel["args"] if name != "Unnamed" else True):
                        is_persistent = True
                        persistent_id = tunnel["id"]
                        break
                
                # Confirm before removing
                if is_persistent:
                    confirm = input(f"Tunnel #{choice} (PID {pid}, Port {port}) is persistent. Remove permanently? (y/n): ").lower()
                else:
                    confirm = input(f"Are you sure you want to terminate tunnel #{choice} (PID {pid})? (y/n): ").lower()
                
                if confirm.startswith('y'):
                    try:
                        # If persistent, remove using pitunnel --remove
                        if is_persistent and persistent_id:
                            subprocess.run(["pitunnel", "--remove", persistent_id], check=True)
                            print(f"Persistent tunnel (ID {persistent_id}) has been removed.")
                        
                        # Terminate the running process regardless
                        os.kill(int(pid), 15)  # Send SIGTERM
                        print(f"Tunnel with PID {pid} has been terminated.")
                        time.sleep(2)
                        break
                    except Exception as e:
                        print(f"Error removing tunnel: {e}")
                        input("Press Enter to continue...")
                        break
                else:
                    print("Operation cancelled.")
                    break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def main_menu():
    """Display the main menu and handle user input."""
    while True:
        clear_screen()
        
        print("=" * 60)
        print("                 PiTunnel Manager                 ")
        print("=" * 60)
        
        processes = display_running_tunnels()
        
        print("\nMenu Options:")
        print("1. Create a new tunnel")
        print("2. Remove a tunnel")
        print("3. Refresh tunnel list")
        print("q. Quit")
        
        choice = input("\nSelect an option: ").lower()
        
        if choice == '1':
            create_tunnel()
        elif choice == '2':
            remove_tunnel(processes)
        elif choice == '3':
            # Just refresh the display - will happen on next loop
            pass
        elif choice == 'q':
            clear_screen()
            print("Exiting PiTunnel Manager. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Please try again.")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        clear_screen()
        print("\nPiTunnel Manager terminated by user. Goodbye!")
        sys.exit(0)
