# Crossout Automation Client: Real-Time Computer Vision and Multi-Threading
This is a game automation tool for Crossout that uses computer vision and a multi-threaded architecture to navigate menus and handle combat.

## Technical Highlights
- **Multi-Threaded Design**: I split the bot into several parts (Camera, Targeting, Pathing, Steering) that run at the same time. This helps the bot stay responsive despite Python's single-core processing limits.
- **Menu Identification**: The bot can recognize where it is in the game (Main Menu, World Map, or Battle) by comparing the screen against saved UI templates.
- **Custom Mapping System**: I created a way to build maps by driving around and recording coordinates. I then processed this data to create "drivable masks" that the navigation system uses.
- **Image Processing Pipelines**: I developed several search algorithms using OpenCV:
  - **Enemy Detection**: Quickly finds enemy markers by filtering for specific colors on the screen.
  - **Player Localization**: Tracks exactly where the player is on the minimap to help with navigation.

## Technical Stack

- **System**: Windows 10, might not work on Windows 11.
- **Computer Vision**: OpenCV (cv2) and NumPy for fast image and data processing.
- **Concurrency**: Python threading and Event triggers for communication between different parts of the bot.
- **Networking**: WebSockets for sending data to the pathfinding server.
- **Automation**: pydirectinput and ctypes for sending keyboard and mouse inputs to the game.

## Key Features

### 1. Targeting System
The bot uses a two-step process to find enemies. It first scans the whole screen to find potential targets, then focuses on a small area around the target to track it more quickly and accurately.

### 2. Navigation
The client calculates how to steer and speed up the car based on paths received from a separate server. This keeps the car moving toward its goal without slowing down the main vision system.

### 3. Map Creation
I built a tool to record my car's position while driving. I used this raw data to draw accurate maps in an image editor, which the bot now uses to avoid walls.

## Project Challenges and Lessons
The biggest challenge was the performance limit of running high-speed image processing in Python. While I optimized the code to be as fast as possible, I learned that a language like C++ or Rust would be better for a project requiring higher frame rates. I also dealt with hit markers and crosshairs covering enemy tags, which is something that could be solved with more advanced text recognition.

## **Project Status**
This bot is **no longer being updated** and was never fully finished. While the core features mostly work, I stopped development because **Python wasn't fast enough** to keep up with the game in real-time.

---

Some parts of the code were AI generated. AI was used while writing this README.md .
