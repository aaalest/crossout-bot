# Crossout Navigation Engine: Distributed Pathfinding and Map Server
This is a backend service for a Crossout automation bot. It handles navigation and map processing on a separate server so the main bot can focus on image processing and combat. It is meant to work with crossoutBotClient.

## Technical Highlights
- **Distributed Backend**: I split the bot into a client and a server. This server handles all the complex pathfinding calculations using FastAPI and WebSockets for fast, real-time communication.
- **Custom Pathfinding**: I wrote a version of the A* algorithm that includes path smoothing. This makes the car's movements look more natural as it follows a route.
- **Map and Grid Management**: The server processes image data into a grid. It handles static obstacles and manages the data needed to find the best way from start to finish.
- **Shared Data Models**: I created a unified system for data (dataclasses and enums) so the client and server can always understand the information they send to each other.

## Technical Stack
- **Backend**: FastAPI and Uvicorn for asynchronous networking.
- **Algorithms**: Custom A* pathfinding and line-of-sight checks.
- **Data Processing**: NumPy and OpenCV for handling grids and image masks.
- **Networking**: WebSockets for low-latency communication.

## How it Works

### 1. Offloading Navigation
Calculating paths through complex maps is slow. By moving this work to a dedicated server, the bot's vision and steering systems can run faster.

### 2. Grid Creation
I implemented image processing tools to turn game screenshots into binary grids. This allows the pathfinding algorithm to know exactly where the car can and cannot drive.

### 3. Scalable Networking
FastAPI's asynchronous features allow the server to handle navigation requests from the client without blocking. This keeps the car moving smoothly even when new paths are being calculated.

## Lessons Learned
Building this server taught me how to manage real-time communication between different parts of a system. I also learned about the performance benefits of offloading heavy calculations to a specialized backend, which is a key part of making automation software reliable.

---

Some parts of the code were AI generated. AI was used while writing this README.md .
