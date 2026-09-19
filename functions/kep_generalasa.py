import asyncio
import os

import filetype

from app_init import *
from pathlib import Path
import base64
import requests
from datetime import datetime, timezone
from flask import request, flash
# REMOVED: néhány kikommentelt, sosem használt import volt itt (rembg, ast.literal_eval, openai,
# deep_translator), valamint a nem használt 'from os import path, listdir' sor.
from PIL import Image
from bleach import clean
from functions.auth_functions import *
import replicate
from functions.rw import cheaper_generate
from sqlalchemy.exc import DataError

with open("styles.txt", mode="r", encoding="utf-8") as f:
    styles = f.readlines()
    styles = [x.strip() for x in styles]

mode = "image_generation"

fortest = False
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
MAXLENGTH = 2000
BACKEND_ADDITION = 400

SEED = 998411
OUTPUT_QUALITY = 100
GO_FAST = True

STABILITY_API_KEY = os.environ.get("STABILITY_API_KEY")

@app.route("/button_click3d", methods=["POST"])
def general3d():
    mode = "generate_3d"
    if not logged_in():
        log(mode, "INFO", f"User not logged in")
        response_data = {'message': 'Hiba', 'error': "You must be logged in!"}
        return jsonify(response_data)

    userid = session.get("userid")

    if r.exists(f"generating:{userid}"):
        log(mode, "INFO", f"User has already have a generation in process")
        response_data = {'message': 'Hiba', 'error': "You already have one generation in process"}
        return jsonify(response_data)

    credits = user_credits(session.get("userid"))

    if credits < 5:
        log(mode, "INFO", f"User ran out of credits.")
        response_data = {'message': 'nocredit', 'error': "Ran out of credits", "nocredit": "nocredit"}
        flash("It seems like you ran out of tool uses to use the 3D object generator. Upgrade your plan to continue creating fabulous 3D objects!")
        return jsonify(response_data)

    try:
        data = request.get_json()
        input_value = clean(data.get('inputValue', ''))[0:MAXLENGTH]

        r.set(f"generating:{userid}", "True", ex=180)

        prompt = input_value[0:MAXLENGTH]

        output = cheaper_generate("3D object, professional, full body object. " + prompt,
                         False, "1:1", "PNG", "free")

        writeable_image = requests.get(output[0], timeout=200).content
        try:
            response = requests.post(
                f"https://api.stability.ai/v2beta/3d/stable-fast-3d",
                headers={
                    "authorization": STABILITY_API_KEY,
                },
                files={
                    "image": writeable_image
                },
                data={},
            )

            filepath = temp_filename(".glb")
            filepath = "./static/t/" + filepath

            with open(filepath, 'wb') as file:
                    file.write(response.content)

        except Exception as e:
            log(mode, "ERROR", f"An error occurred: {e}")
            r.delete(f"generating:{userid}")
            return jsonify({"nsfw": "nsfw"})

        log(mode, "INFO", f"3D generation was successful. Prompt: {input_value}")

        r.delete(f"generating:{userid}")

        charge_user(userid, 20)

        try:
            db.session.add(
                Transactions(user_id=userid, text=mode, credits_cost=5,
                             created_at=datetime.now(), type=mode))
            db.session.commit()
        except Exception as e:
            log(mode, "ERROR", f"Error while saving transaction data to database: {e}.")
            pass

        response_data = {'message': 'Done', 'filepath': filepath}

        return jsonify(response_data)

    except Exception as e:
        r.delete(f"generating:{userid}")
        log(mode, "ERROR", f"An error occurred while generating the 3D model. (ERROR: {e})")
        response_data = {'message': 'Hiba', 'error': "We couldn't generate your 3D object. It was either a server-side error or NSFW Detection. No credits were charged. If you don't think it was an nsfw detection, please contact us if the problem doesn't disappear in a few minutes."}
        return jsonify(response_data), 500

@app.route("/button_click", methods=["POST"])
def general():
    if not logged_in():
        return redirect(url_for("belepes_load"))

    userid = session.get("userid")
    if r.exists(f"generating:{userid}"):
        log(mode, "INFO", f"User already has a generation in process.")
        response_data = {'message': 'Hiba', 'error': "You already have one generation in process"}
        return jsonify(response_data)

    data = request.form
    model = clean(data.get("model", None))

    if model not in ("imagegen1", "imagegen2", "image-edit"):
        r.delete(f"generating:{userid}")
        return jsonify({"error": "A model must be selected!"})

    if model == "imagegen1":
        cost = 1
    elif model == "imagegen2":
        cost = 10
    else:
        cost = 15
    file = request.files.get('reference_image', None)

    if file is not None:
        file_type = filetype.guess(file.stream.read(2048)).extension.upper()
        file.stream.seek(0)

    if model == "image-edit" and file is not None and file_type not in {"JPG", "PNG", "JPEG", "WEBP"}:
        r.delete(f"generating:{userid}")
        return jsonify({"error": "There must be an image attached which is either JPG (JPEG), PNG, or WEBP!"})

    remb = clean(data.get('remb', "Off"))[0:5]
    remb = "Off"

    if remb not in {"Off", "On"}:
        remb = "Off"

    if remb == "On":
        remb = True
    else:
        remb = False

    if user_credits(userid) < cost:
        log(mode, "INFO", f"User ran out of credits.")
        response_data = {'message': 'nocredit', 'error': "You ran out of credits", "nocredit": "nocredit"}
        flash("It seems like you ran out of credits to use the image generator. Upgrade your plan to continue creating fabulous images!")
        return jsonify(response_data)

    if file is not None:
        file = base64.b64encode(file.read()).decode("utf-8")

    r.set(f"generating:{userid}", "True", ex=180)

    return generalas(session, userid, data, remb, model, file, cost)


def generalas(session, userid, data, remove_background_too, modell, image, cost):
    try:
        timefullstart = time()

        input = clean(data.get('inputValue', ''))[0:MAXLENGTH + BACKEND_ADDITION]

        aspect_ratio = clean(data.get('arany', '1:1'))

        if aspect_ratio not in ["1:1", "9:16", "16:9", "3:4", "4:3"]:
            aspect_ratio = "1:1"

        stilus = clean(data.get('style', "None"))
        userid = session.get("userid")

        balance = user_credits(userid)
        plan = user_plan(userid)

        #styles = all styles without None
        if stilus in styles[19::] and plan == "free":
            session.pop("style", None)
            response_data = {'message': 'Hiba', 'error': "The style you selected is a premium style. Upgrade your plan to Pro or higher, or select another style."}
            r.delete(f"generating:{userid}")
            return jsonify(response_data)

        session["prompt"] = input.replace('"', '&quot;').replace("'", '&#x27;')
        if stilus not in stilusok:
            stilus = "None"

        session["style"] = stilus
        session["aspect_ratio"] = aspect_ratio

        log(mode, "INFO", f"User has started image generation with the prompt: {input}. (BALANCE: {balance}).")

        try:
            try:
                prompt = input[0:MAXLENGTH] + ", " + stilusok[stilus]
            except Exception as e:
                log(mode, "ERROR", f"Error while fetching the prompt. {e}")
                prompt = input[0:MAXLENGTH]

            flux_timer_start = time()
            filename = gen(session.get("userid"), prompt, aspect_ratio, remove_background_too, modell, image)  # EZ IS GENERÁLJA A KÉPET
            flux_time = time() - flux_timer_start

             #credits_to_charge_with)
            charge_user(userid, cost)
            try:
                db.session.add(
                    Images(user_id=userid, prompt=input.replace('"', '&quot;').replace("'", '&#x27;'), width=0, height=0, created_at=datetime.now(),
                           cost=filename[1],
                           name=filename[0], arany=aspect_ratio, stilus=stilus, modell=modell))
                db.session.add(Transactions(user_id=userid, text=input.replace('"', '&quot;').replace("'", '&#x27;'), credits_cost=1, created_at=datetime.now(), type=mode))
                db.session.commit()

            except Exception as e:
                log(mode, "CRITICAL", f"A problem occurred server-side when trying to add a new image in the database, transaction or images error, error: {e}")
                db.session.add(
                    Images(user_id=userid, prompt=input.replace('"', '&quot;').replace("'", '&#x27;'), width=0,
                           height=0, created_at=datetime.now(),
                           cost=filename[1],
                           name=filename[0], arany=aspect_ratio, stilus=stilus, modell=modell))
                charge_user(userid, -cost)
                db.session.commit()

            r.delete(f"generating:{userid}")

            response_data = {'message': 'Done', "filepath" :filename[0]}

            log(mode, "INFO", f"Success. Generated in {round(time() - timefullstart, 6)}, (FLUX TIME: {round(round(flux_time,4), 4)}). Prompt: {input}")
            return jsonify(response_data)

        except Exception as e:
            r.delete(f"generating:{userid}")
            log(mode, "ERROR", f"An error occurred: {e} ")
            response_data = {'message': 'Hiba', 'error': "Unexpected Error Happened"}
            return jsonify(response_data)
    except Exception as e:
        r.delete(f"generating:{userid}")
        log(mode, "ERROR", f"An error occurred: {e} ")
        response_data = {'message': 'Hiba', 'error': "Unexpected Error Happened"}
        return jsonify(response_data)


def now():
    return datetime.now()


def gen(userid, prompt, aspect_ratio, remove_background_too, modell, image):
    cheaper = False
    try:
        output = cheaper_generate(prompt, cheaper, aspect_ratio, "jpg", user_plan(userid), modell, image)
        writeable_image = requests.get(output[0], timeout=200).content
        cost = output[1]
    except Exception as e:
        log(mode, "ERROR", f"Runware error: {e}, not continuing with replicate ($0,003 usd)")
        return Exception(
            "Oops! It's unusual, but we ran into a server exhaust! Please wait a few minutes before trying again!")

    path_to_save = "./static/photo-hd"
    thumbnail_path = "./static/photo"

    filename = temp_filename(".jpeg")
    with open(f"{path_to_save}/{filename}", "wb") as f:
        f.write(writeable_image)

    if remove_background_too:
        with open(f"{path_to_save}/{filename}", mode="rb") as f:
            #rmed = rembg.remove(f.read())
            rmed = f.read()

        with open(f"{path_to_save}/{filename}", "wb") as file:
            file.write(rmed)

    if not remove_background_too:
        a = Image.open(f"{path_to_save}/{filename}")
        resized_a = a.resize((int(a.width / 1.1), int(a.height / 1.1)), Image.Resampling.LANCZOS)
        resized_a.save(f"{thumbnail_path}/{filename}")
        a.save(f"{thumbnail_path}/{filename}")
    else:
        with open(f"{thumbnail_path}/{filename}", "wb") as file:
            file.write(rmed)

    return [filename, cost]
