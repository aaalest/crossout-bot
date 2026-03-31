# Crossout Bot Server

## Overview

This project contains the server-side navigation engine for the Crossout bot. It handles pathfinding, grid processing, and network communication so the client can focus on screen reading and control logic.

The server is designed to offload heavier navigation work from the client and return movement decisions with low latency.

## Responsibilities

- Accept navigation-related requests from the client
- Maintain map and grid data used for routing
- Run pathfinding and path simplification logic
- Return movement results over WebSocket connections

## Technical Stack

- Python 3.11
- FastAPI and Uvicorn for the server runtime
- WebSockets for low-latency communication
- NumPy, OpenCV, and SciPy for grid and path processing

## How It Works

### API layer

`src/main.py` starts a FastAPI application that exposes:

- a WebSocket endpoint at `/communication`
- HTTP routes used for basic server responses and map-related operations

### Pathfinding

The navigation logic is implemented under `src/pathfinding_algorithm/`. The server processes map data, computes traversable paths, and returns movement output that the client can translate into steering behavior.

### Grid management

The grid layer converts map-related data into structures suitable for routing and obstacle checks. This keeps path calculation separate from the client-side rendering and CV loop.

## Setup

### Install dependencies

```bash
cd server
pip install -r requirements.txt
```

## Run

From the project directory:

```bash
cd src
python main.py
```

The server runs on port `5762` by default.

## Status

This project is no longer under active development, but it preserves the pathfinding and networking architecture used by the bot.

## Notes

- The server is intended to be used together with the client in [../client](../client).
- Some files and this documentation were AI-assisted during development.
