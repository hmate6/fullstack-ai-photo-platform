import base64
import json
from os import getenv

import requests
from uuid import uuid4

mode = "runware_generation"
RUNWARE_API = getenv("RUNWARE_API")

def enhance(input_location, format):
    url = 'https://api.runware.ai/v1'

    with open(input_location, mode="rb") as f:
        inputImage = base64.b64encode(f.read()).decode("utf-8")

    taskUUID = str(uuid4())

    headers = {
        'Content-Type': 'application/json'
    }
    data = [
        {
            "taskType": "authentication",
            "apiKey": RUNWARE_API
        },
        {
            "taskType": "imageUpscale",
            "taskUUID": taskUUID,
            "upscaleFactor": 2,
            "inputImage": inputImage,
            "outputType": ["URL"],
            "model": "runware:504@1",
            "includeCost": True,
            "outputFormat": format
        }
    ]

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=200)
        response = response.json()
    except requests.exceptions.Timeout:
        log(mode, "ERROR", f"Timeout-error while enhancing image, timeout error), uuid={taskUUID}")
        return "Timeout"
    except Exception as e:
        log(mode, "ERROR", f"Error while generating image: ({e}), uuid={taskUUID}")
        return "Error"

    if "errors" in response:
        log(mode, "ERROR", f"Error upscaling image: {response}, uuid={taskUUID}")
        return "Error"
    try:
        url = response["data"][0]["imageURL"]
        price = response["data"][0]["cost"]
    except Exception as e:
        print(response)
        log(mode, "ERROR", f"Error while fetching data from json: {e}, uuid={taskUUID}")
        return "Error"

    return [url, price]
