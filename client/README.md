# Crossout Bot Client

## Overview

This project contains the client-side bot runtime for Crossout. It is responsible for reading the game state from the screen, identifying targets and menus, requesting navigation data from the server, and sending movement inputs back to the game.

The client is built around a multithreaded architecture so image processing, targeting, navigation, and control loops can run concurrently.

## Responsibilities

- Capture and interpret the game window
- Detect menus, player, enemies, allyes locations, and enemy markers on screen
- Communicate with the navigation server over WebSockets
- Execute steering, throttle, and camera actions

## Technical Stack

- Python 3.11
- OpenCV, NumPy, Pillow, and MSS/DXCam for screen and image processing
- `threading` and event-driven coordination for concurrent subsystems
- `websockets`, `aiohttp`, and `requests` for communication
- `pydirectinput`, `pywin32`, `keyboard`, and `pynput` for Windows input handling

## How It Works

### Runtime flow

`src/main.py` starts the main bot loop and launches the background processors used for:

- map reading
- camera control
- target lock-on
- pathing
- steering
- throttle
- display output

The main loop coordinates these processors at different frame rates so heavier CV tasks do not run every frame.

### Navigation

The client does not calculate full paths locally. It sends state to the server, receives movement/path data, and converts that into steering and throttle behavior.

### Mapping and UI detection

The client includes readers and tools for:

- identifying the current menu or battle state
- localizing the player on the minimap
- detecting enemy markers
- working with recorded map data and overlays

## Setup

### Requirements

- Windows 10
- Python 3.11
- Crossout running locally
- A running instance of the companion [server](/server)

### Install dependencies

```bash
cd client 
pip install -r requirements.txt
```

## Run

From the project directory:

```bash
cd src
python main.py
```

## Status

This project is no longer being updated and was not fully finished. The main limitation encountered during development was Python-side performance for high-frequency image processing.

## Notes

- Some files and this documentation were AI-assisted.
