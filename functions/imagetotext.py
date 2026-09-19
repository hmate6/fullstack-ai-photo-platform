import filetype  # CHANGED (ujra): 'imghdr' helyett -- a Python 3.13 teljesen eltavolitotta ezt a modult,
# emiatt ez a fajl (es vele az egesz app, mert a main.py importalja) elszallt volna inditaskor.
import requests

from app_init import *
from functions.auth_functions import *
from PIL import Image, ExifTags
from pathlib import Path
import io


MAX_FINAL_SIZE = 1024 * 1024

OCR_SPACE_API_KEY = getenv("OCR_SPACE_API_KEY")

def save_image_max_1mb(file_storage, out_path):
    """
    Saves the image to out_path.
    If image > 1MB, it is recompressed to <= 1MB.
    """
    img = Image.open(file_storage.stream)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    quality = 95
    width, height = img.size

    while True:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        size = buffer.tell()

        if size <= MAX_FINAL_SIZE:
            with open(out_path, "wb") as f:
                f.write(buffer.getvalue())
            break

        if quality > 30:
            quality -= 5
        else:
            width = int(width * 0.9)
            height = int(height * 0.9)
            img = img.resize((width, height), Image.Resampling.LANCZOS)  # CHANGED (ujra): konzisztencia a projekt tobbi reszevel
            quality = 95

@app.route('/upload', methods=['POST'])
def ocr():
    try:
        if not logged_in():
            return jsonify({"error": "You are not logged in"})
        userid = session.get("userid")

        uploaded_files = request.files.getlist("images")
        length_of_uploaded_files = len(uploaded_files)

        if userid is not None and user_credits(userid) < length_of_uploaded_files:
            return jsonify({"out_of_credits": "You don't have enough credits to scan the images!"})


        if length_of_uploaded_files > 5:
            return jsonify({"more_than_limit": "More than 5 images were attached. "
                                               "We will allow scanning more images in the future, but for now, maximum 5 images is allowed."})

        # CHANGED (ujra): minden fajlt elore ellenorzunk (tipus + meret), mielott barmelyiket feldolgoznank.
        # Korabban ha egy kep tipusa nem egyezett, az a kep csendben kimaradt a valaszbol, es ez
        # osszecsusztatta a frontend oldali kep-sorrendet (files[index]) az eredmenyekkel (response[index]).
        for file in uploaded_files:
            guessed_type = filetype.guess(file.stream.read(2048))
            file.stream.seek(0)
            file_extension = ("." + guessed_type.extension.lower()) if guessed_type else ""

            if file_extension not in {'.jpg', '.jpeg', '.png'}:
                return jsonify({"error": f"Unsupported file type for '{file.filename}'. Only JPG, JPEG and PNG images are accepted."})

            file_size = len(file.read())
            file.seek(0)
            if file_size > 10 * 1024 * 1024:
                return jsonify({"error": f"'{file.filename}' exceeds the 10 MB size limit!"})

        response_data = []

        for file in uploaded_files:
            file_size = len(file.read())
            file.seek(0)

            filename_extension = Path(file.filename).suffix
            filepath = temp_filename(filename_extension)
            filepath = "./static/t/" + filepath

            if file_size > 1024 * 1024:
                save_image_max_1mb(file, filepath)
            else:
                file.save(filepath)

            correct_image_orientation(filepath)  # ADDED (ujra): ez a fuggveny meg volt irva, de sehol nem hivodott meg

            result = detect_document(filepath)
            response_data.append(result)

        charge_user(userid, length_of_uploaded_files)

        try:
            db.session.add(
                Transactions(user_id=userid, text="image_to_text", credits_cost=length_of_uploaded_files,
                             created_at=datetime.now(), type="image_to_text"))
            db.session.commit()
        except Exception as e:
            log("image_to_text", "ERROR", f"Error while saving transaction data to database: {e}.")
            pass
        print(response_data)
        return jsonify(response_data)
    except Exception as e:
        log("image_to_text", "CRITICAL", f"Error while OCRing: {e}")
        return jsonify({"error": "A problem occurred while scanning your image. Try again later, or report it by contacting us."})

def correct_image_orientation(image_path):
    """Corrects the orientation of the image based on its EXIF data."""
    with Image.open(image_path) as img:
        try:

            exif = img.getexif()
            orientation_tag = next((k for k, v in ExifTags.TAGS.items() if v == 'Orientation'), None)
            if exif is not None and orientation_tag is not None:
                orientation_value = exif.get(orientation_tag)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except Exception as e:
            print(f"Error correcting orientation: {e}")

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(image_path, format="JPEG")

def detect_document(path):
    """Detects text and coordinates using the OCR.space API."""

    payload = {
        'apikey': OCR_SPACE_API_KEY,
        'language': 'eng',
        'isOverlayRequired': True,
        'FileType': 'Auto',
    }

    with open(path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'file': f},
            data=payload,
        ).json()

    if response.get('OCRExitCode') != 1:
        log("image_to_text", "ERROR", f"OCR.space hiba: {response.get('ErrorMessage')}")
        return {"full_text": "", "boxes": [], "error": response.get('ErrorMessage')}

    text_annotations_list = []
    full_text = ""

    for result in response.get('ParsedResults', []):
        full_text += result.get('ParsedText', '')

        overlay = result.get('TextOverlay', {})
        for line in overlay.get('Lines', []):
            for word_info in line.get('Words', []):
                word_text = word_info.get('WordText')

                left = word_info.get('Left')
                top = word_info.get('Top')
                width = word_info.get('Width')

                word_dict = {
                    'x': int(left + (width / 2)),
                    'y': int(top),
                    'character': word_text
                }
                text_annotations_list.append(word_dict)

    return {"full_text": full_text, "boxes": text_annotations_list}
