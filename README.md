# PiTunnel Manager

A terminal-based configurator for managing PiTunnel connections. This script provides a menu-driven interface to:

- View currently running PiTunnel processes
- Create new tunnels to expose local services to the internet
- Remove/terminate existing tunnels

## Features

- List all running PiTunnel processes with their PIDs, ports, and tunnel names
- Create new tunnels with customizable options:
  - Local port to expose
  - HTTP tunnels
  - Custom tunnel names (subdomains)
  - Persistent tunnels that automatically start on device boot
- Terminate existing tunnels

## Requirements
You need an account at https://www.pitunnel.com/ and to install PiTunnel on your Rasbperry Pi.

## Usage

1. Make the script executable:
   ```
   chmod +x pitunnel_manager.py
   ```

2. Run the script:
   ```
   ./pitunnel_manager.py
   ```

3. Follow the on-screen menu to manage your tunnels.

## Requirements

- Python 3.6+
- PiTunnel CLI installed and configured on your device

## Note

This script assumes the `pitunnel` command is available in your PATH. Make sure PiTunnel is properly installed on your system before using this manager.
