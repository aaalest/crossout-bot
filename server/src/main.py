import time
import re
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
import numpy as np
from enum import Enum, auto
import cv2
import uvicorn
import json
import threading
import pickle
import copy
import base64
from starlette.responses import Response, JSONResponse
from fastapi import APIRouter, Request, HTTPException, FastAPI, File, UploadFile, Form
from dataclasses import dataclass, asdict, field
from typing import Union

from logger import logger
import custom_types as tp


# np.set_printoptions(threshold=np.inf, linewidth=np.inf)
app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.websocket("/communication")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            await asyncio.sleep(0.001)  # Sleep to avoid tight loop
            input_data: str = await websocket.receive_text()
            input_data: dict = json.loads(input_data)
            logger.info(f'input_data: {input_data}')
            output_data = {}

            # mark point function
            mark_point_input = input_data.get("mark_car_point_input")
            if mark_point_input:
                mark_point_input: tp.MarkCarPointInput = tp.decode(mark_point_input)
                grid.manager.mark_car_point(mark_point_input)
                output_data["mark_point"] = {"status": "success"}

            # calculate actions function
            movement_input = input_data.get("car_movement_input")
            if movement_input:
                now = time.time()
                car_movement_input: tp.CarMovementInput = tp.decode(movement_input) if movement_input else None
                logger.info(f'car_movement_input: {car_movement_input}')

                movement_output: tp.CarMovementOutput = grid.manager.calculate_land_actions()
                logger.info(f'calculate_actions time: {time.time() - now}')
                output_data["movement"] = tp.encode(movement_output) if movement_output else None,

            # reply with output
            output_data["status"] = "success"
            logger.info(f'sending: {movement_output}')
            await websocket.send_json(output_data)
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except tp.CalculationFailError as e:
            logger.error(f"Failed to get data: {e}")
            try:
                await websocket.send_json({"status": "error", "error": str(e)})
            except Exception as e:
                logger.error(f"An error occurred: {e}")
        except Exception as e:
            raise e
            logger.error(f"An error occurred: {e}")


@app.get("/")
async def get(request):
    return templates.TemplateResponse("index.html", {"request": request})


# @app.post("/mark_car_point")
# async def mark_car_point(metadata: str = Form(...)) -> Response:
#     metadata: dict = json.loads(metadata)
#     mark_point_input = metadata.get("mark_point_input")
#     mark_point_input: tp.MarkCarPointInput = tp.decode(mark_point_input)
#     # map_name = mark_point_input.map_type.name
#     # img = getattr(var.car_maps_data, map_name).grid.copy()
#     # getattr(var.car_maps_data, map_name).grid = grid.mark_car_point(img, mark_point_input.player_data, mark_point_input.mark_type)
#     grid.mark_car_point(var, mark_point_input)
#     # cv2.imwrite(f'maps/{map_obj}_show.png', getattr(var.car_maps_data, map_obj.name).grid)
#     # # cv2.imshow(map_name, maps[map_name]["img"])
#     # cv2.waitKey(0)
#     logger.info(f'Received data: {mark_point_input}')
#
#     return Response(headers={
#         "metadata": json.dumps({
#             "status": "ok"
#         })
#     })


@app.post("/save_car_map")
async def save_car_map(metadata: str = Form(...)):
    metadata: dict = json.loads(metadata)
    mark_point_input = metadata.get("map_obj")
    map_obj: tp.CarMaps = tp.decode(mark_point_input)
    # grid.save_car_map(var, map_obj)

    return Response(headers={
        "metadata": json.dumps({
            "status": "ok"
        })
    })


import grid


if __name__ == "__main__":
    # threading.Thread(target=grid.show_map_loop, args=(var,)).start()

    # uvicorn.run(app, host="127.0.0.1", port=5000)
    uvicorn.run(app, host="0.0.0.0", port=5762)
