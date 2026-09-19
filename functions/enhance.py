import base64
import json
from os import getenv  # ADDED: kell a RUNWARE_API env-változóhoz
from uuid import uuid4

import filetype
import imghdr
import secrets
from os import listdir
from string import ascii_letters, digits
from random import randint
from flask import flash, jsonify

from PIL import Image

from functions.auth_functions import log, temp_filename, charge_user, user_credits
import requests
from replicate.exceptions import ModelError

from app_init import *
import replicate
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp', "webp"}

mode = "enhance"
RUNWARE_API = getenv("RUNWARE_API")

@app.route('/enhance-images-post', methods=['POST'])
def enhance_images():
    if not logged_in():
        return jsonify({"error": "Not logged in!"})

    userid = session.get("userid")

    if r.exists(f"generating:{userid}"):
        return jsonify({"error": "You have an another generation or enhancement in process!"})

    if user_credits(userid) < 2:
        flash("It seems like you ran out of credits to enhance your images. ")
        return jsonify({'nocredit': 'Ran out of credits'})

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']

    scale = request.form.get("scale")

    try:
        scale = int(scale)
    except ValueError:
        scale = 1

    if scale not in (2, 4):
        scale = 4

    file_type = filetype.guess(file.stream.read(2048)).extension.upper()
    file.stream.seek(0)

    if file and file_type in {"JPG", "PNG", "JPEG", "WEBP"}:
        try:
            r.set(f"generating:{userid}", "True", ex=180)

            if file.content_type not in ['image/jpeg', 'image/png', 'image/webp', 'image/bmp']:
                return jsonify({"error": "Unsupported file type. Must be JPG/JPEG, PNG, BMP or WEBP."})

            file_size = len(file.read())
            file.seek(0)
            if file_size > 10 * 1024 * 1024:
                r.delete(f"generating:{userid}")
                return jsonify({"error": "File size exceeds the 10 MB limit"})

            filename = secure_filename(file.filename)

            file_extension = filename[filename.rfind(".")::]
            file_path = temp_filename(file_extension)
            file_path = "./static/t/" + file_path
            file.save(file_path)
            upload_path = file_path[2::]

            with Image.open(file_path) as img:
                width, height = img.size
                if width > 2000 or height > 2000:
                    resized_a = img.resize((int(img.width / 1), int(img.height / 1)), Image.Resampling.LANCZOS)
                    resized_a.save(file_path)

            url = 'https://api.runware.ai/v1'

            with open(file_path, mode="rb") as f:
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
                    "upscaleFactor": scale,
                    "inputImage": inputImage,
                    "outputType": ["URL"],
                    "model": "runware:504@1",
                    "includeCost": True,
                    "outputFormat": file_type
                }
            ]

            log("enhance", "INFO", f"Enhancement started {file_path}")
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=200)
                print(response)
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

            writeable_image = requests.get(url, timeout=200).content

            log("enhance", "INFO", f"Enhancement ended {file_path}")

            charge_user(session.get("userid"), 2)

            try:
                db.session.add(
                    Transactions(user_id=userid, text="enhance", credits_cost=price, #runware cost is the credits_cost
                                 created_at=datetime.now(), type="enhance"))
                db.session.commit()
            except Exception as e:
                log("enhance", "ERROR", f"Error while saving transaction data to database: {e}.")
                pass

            new_file_path = temp_filename(file_extension)
            new_file_path = "./static/t/" + new_file_path

            with open(new_file_path, mode="wb") as f:
                f.write(writeable_image)

            r.delete(f"generating:{userid}")
            return jsonify({'enhanced_image_url': new_file_path[1::]}), 200
        except Exception as e:
            r.delete(f"generating:{userid}")
            log("enhance", "CRITICAL", f"Error while enhancing image, error: {e}")
            return jsonify({'error': 'A problem occurred while enhancing your image. Try again later, or report it by contacting us.'})

    else:
        return jsonify({'error': 'Invalid file type. We only support enhancing images that are .jpg(.jpeg), .png, .webp and .bmp'})
