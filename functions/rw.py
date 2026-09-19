import json
from os import getenv

import requests
from uuid import uuid4
from functions.auth_functions import log

mode = "runware_generation"
# CHANGED: pár elszórt, kikommentelt debug/kísérleti sor törölve (print, régi szélesség/magasság, checkNSFW), működés nem változott
RUNWARE_API = getenv("RUNWARE_API")

def cheaper_generate(input, cheaper, aspect_ratio, format, plan, modell, image):
    url = 'https://api.runware.ai/v1'
    if aspect_ratio == "1:1":
        width, height = 1024, 1024
    elif aspect_ratio == "16:9":
        width, height = 1376, 768
    elif aspect_ratio == "9:16":
        width, height = 768, 1376
    elif aspect_ratio == "4:3":
        width, height = 1184, 896
    elif aspect_ratio == "3:4":
        width, height = 896, 1184
    else:
        width, height = 1024, 1024

    taskUUID = str(uuid4())

    if len(input) < 3:
        amount = 3 - len(input)
        input += "".join(" " for x in range(amount))

    headers = {
        'Content-Type': 'application/json'
    }
    data = [
        {
            "taskType": "authentication",
            "apiKey": RUNWARE_API
        },
        {
            "taskType": "imageInference",
            "taskUUID": taskUUID,
            "positivePrompt": input,
            "width": width,
            "height": height,
            "model": "runware:400@4" if modell=="imagegen1" else "runware:400@3" if modell=="imagegen2" else "prunaai:2@1",
            "numberResults": 1,
            "includeCost": True,
            "outputFormat": format,
        }
    ]

    if image is not None:
        data[1]["inputs"] = {"referenceImages": [image]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=200)
        response = response.json()
    except requests.exceptions.Timeout:
        log(mode, "ERROR", f"Timeout-error while generating image ({width}, {height}), uuid={taskUUID}")
        return "Timeout"
    except Exception as e:
        log(mode, "ERROR", f"Error while generating image: ({e}) ---------- OTHER INFOS: WIDTH AND HEIGHT({width}, {height}), uuid={taskUUID}")
        return "Error"

    if "errors" in response:
        log(mode, "ERROR", f"Error while generating image: {response} ({width}, {height}), uuid={taskUUID}")
        return "Error"
    try:
        url = response["data"][0]["imageURL"]
        price = response["data"][0]["cost"]
    except Exception as e:
        print(response)
        log(mode, "ERROR", f"Error while fetching data from json: {e} -- OTHER INFOS ({width}, {height}), uuid={taskUUID}")
        return "Error"

    return [url, price]
