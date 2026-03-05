# Crossout Automation: Distributed Bot System

This project is a game automation system for Crossout, consisting of a high-speed client and a dedicated pathfinding server. It was developed to explore real-time computer vision, multi-threaded architecture, and distributed systems.

## Project Overview

The system is split into two main components to optimize performance:
1.  **[client](./client)**: Handles real-time screen capture, player location, enemy detection, game state awareness, and input simulation.
2.  **[server](./server)**: A dedicated backend that manages map data and performs pathfinding calculations.

## Core Features

- **Real-Time Computer Vision**: Uses OpenCV for fast detection of enemy markers and player localization on the minimap.
- **Distributed Navigation**: Offloads pathfinding to a FastAPI-based server to maintain high frame rates on the client.
- **Multi-Threaded Execution**: The client runs 6+ concurrent threads to handle independent tasks like camera input and target tracking.
- **Intelligent Menu Navigation**: Automatically recognizes and navigates game menus by analyzing UI templates.
- **Custom Mapping Tools**: Includes a system for recording and generating high-fidelity drivable masks from in-game data.

## Technical Stack

- **System**: Windows 10
- **Languages**: Python 3.11
- **Computer Vision**: OpenCV, NumPy
- **Backend & API**: FastAPI, Uvicorn, WebSockets
- **Automation**: PyDirectInput, Win32API, ctypes
- **Algorithms**: Custom A* with path smoothing, ROI optimization

## Project Status and Lessons

This project was built for educational purposes and is no longer being actively updated. The development provided several key engineering insights:
- **Language Selection**: High-frequency image processing in Python faces performance bottlenecks. For higher FPS, moving core CV tasks to C++ or Rust would be more effective.
- **Distributed Design**: Separating navigation from vision significantly improved client-side responsiveness.

---
*Note: This project is for educational purposes only. Using automation in multiplayer games may violate Terms of Service.*
