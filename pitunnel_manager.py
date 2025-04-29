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
        # Instead of ps aux, use pitunnel --status to get actual tunnels
        # First try the specific command for PiTunnel status
        try:
            status_result = subprocess.run(
                ["pitunnel", "--status"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # If --status worked, parse its output
            if status_result.returncode == 0:
                parsed_processes = []
                lines = status_result.stdout.strip().splitlines()
                
                # Parse table format if it exists
                table_start = False
                for line in lines:
                    if 'PID' in line and 'Port' in line and 'Type' in line:
                        table_start = True
                        continue
                    if table_start and len(line.strip()) > 0 and not line.startswith('+---'):
                        parts = [p.strip() for p in line.split('|') if p.strip()]
                        if len(parts) >= 4:
                            pid = parts[0]
                            port = parts[1]
                            tunnel_type = parts[2]
                            name = parts[3] if len(parts) > 3 else "Unnamed"
                            
                            parsed_processes.append({
                                "pid": pid,
                                "port": port,
                                "name": name,
                                "type": tunnel_type,
                                "command": f"pitunnel --port={port}" + (f" --name={name}" if name != "Unnamed" else "")
                            })
                
                if parsed_processes:
                    return parsed_processes
        except (subprocess.SubprocessError, FileNotFoundError):
            # If --status failed, fall back to ps command but with improved filtering
            pass
            
        # Fallback: use ps but with better filtering
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        processes = []
        for line in result.stdout.splitlines():
            # Only include lines with pitunnel command (not processes containing pitunnel in name)
            # Exclude defunct processes and our manager script
            if (" pitunnel " in line or line.endswith(" pitunnel")) and \
               "<defunct>" not in line and \
               "pitunnel_manager.py" not in line and \
               "pitunnel_terminal" not in line:
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
                            # The pitunnel command will handle stopping the running process
                        else:
                            # For non-persistent tunnels, use pitunnel --stop with port
                            subprocess.run(["pitunnel", "--stop", f"--port={port}"], check=True)
                            print(f"Tunnel on port {port} has been stopped.")
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

def reload_tunnels():
    """Reload all persistent tunnels (remove and recreate them)."""
    persistent_tunnels = get_persistent_tunnels()
    
    if not persistent_tunnels:
        print("\nNo persistent tunnels found to reload.")
        input("Press Enter to continue...")
        return
    
    print("\nPersistent Tunnels:")
    print("-" * 60)
    print(f"{'#':<3} {'ID':<5} {'Arguments'}")
    print("-" * 60)
    
    for i, tunnel in enumerate(persistent_tunnels, 1):
        print(f"{i:<3} {tunnel['id']:<5} {tunnel['args']}")
    
    confirm = input("\nAre you sure you want to reload all persistent tunnels? (y/n): ").lower()
    if not confirm.startswith('y'):
        print("\nReload cancelled.")
        time.sleep(1)
        return
    
    print("\nReloading tunnels...")
    # Store the configurations
    tunnel_configs = []
    for tunnel in persistent_tunnels:
        # Parse the arguments into a list
        args = tunnel['args'].split()
        tunnel_configs.append(args)
        
        # Remove the tunnel
        try:
            subprocess.run(["pitunnel", "--remove", tunnel['id']], check=True)
            print(f"Removed tunnel ID {tunnel['id']}")
            # The pitunnel command will handle stopping the running process
        except Exception as e:
            print(f"Error removing tunnel ID {tunnel['id']}: {e}")
    
    # Wait a moment for processes to terminate
    time.sleep(2)
    
    # Recreate the tunnels
    for i, args in enumerate(tunnel_configs, 1):
        try:
            # Add the actual pitunnel command to the beginning
            cmd = ["pitunnel"] + args
            subprocess.Popen(cmd)
            print(f"Recreated tunnel {i}/{len(tunnel_configs)} with args: {' '.join(args)}")
            # Small delay to avoid potential issues with starting multiple tunnels at once
            time.sleep(0.5)
        except Exception as e:
            print(f"Error recreating tunnel: {e}")
    
    print("\nAll tunnels have been reloaded!")
    input("Press Enter to continue...")

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
        print("3. Reload all persistent tunnels")
        print("4. Refresh tunnel list")
        print("q. Quit")
        
        choice = input("\nSelect an option: ").lower()
        
        if choice == '1':
            create_tunnel()
        elif choice == '2':
            remove_tunnel(processes)
        elif choice == '3':
            reload_tunnels()
        elif choice == '4':
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
