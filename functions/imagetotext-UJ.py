import pytesseract  # CHANGED: 'requests' + OCR.space kulso API-hivas helyett -- a .env-ben az
# OCR_SPACE_API_KEY ures volt, emiatt MINDEN keres hibaval tert vissza es a felhasznalo semmilyen
# szoveget / pozicio-boxot nem latott. Helyette helyi, kulcs nelkuli Tesseract OCR motort hasznalunk
# (nincs kulso halozati fuggoseg, nincs havi limit, nincs tobbe API kulcs kezeles).
import filetype  # CHANGED: 'imghdr' helyett -- az imghdr modult a Python 3.13 mar eltavolitotta,
# emiatt ez a fajl (es vele egyutt az egesz app, mert a main.py importalja) elszallt volna inditaskor.
# A filetype mar amugy is hasznalva van a projektben (functions/enhance.py), igy konzisztens is.

from app_init import *
from functions.auth_functions import *
from PIL import Image, ExifTags  # CHANGED: korábban a PIL Image kétszer is importálva volt
from pathlib import Path
import io
# REMOVED: 'from google.cloud import vision' és 'import os' -- egyik sem volt sehol használva ebben a
# fájlban (a szövegfelismerés most a helyi Tesseract OCR motort használja, nem Google Vision-t vagy OCR.space-t)

MAX_FINAL_SIZE = 1024 * 1024

# CHANGED: OCR_SPACE_API_KEY mar nem kell (nincs tobbe kulso API hivas).
# A felismerendo nyelv a .env-bol allithato (pl. TESSERACT_LANG=hun vagy TESSERACT_LANG=eng+hun),
# alapertelmezetten "eng", mert ez mindig resze a Tesseract alap telepitesenek -- magyar nyelvi
# csomag (hun.traineddata) kulon telepitest igenyel a szerveren/gepen.
TESSERACT_LANG = getenv("TESSERACT_LANG", "eng")

# CHANGED: opcionalis -- ha a tesseract.exe nincs a PATH-on (pl. Windows-on alapertelmezetten NINCS
# rajta, hacsak nem pipaltad ki telepiteskor), a .env-ben megadhato a teljes eleresi utja, pl.:
# TESSERACT_CMD_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
_tesseract_cmd_path = getenv("TESSERACT_CMD_PATH")
if _tesseract_cmd_path:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd_path

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
            img = img.resize((width, height), Image.Resampling.LANCZOS)  # CHANGED: a projekt tobbi helyen (pl. kep_generalasa.py) is Image.Resampling.LANCZOS-t hasznal, konzisztencia
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

        # CHANGED: minden fajlt elore ellenorzunk (tipus + meret), mielott barmelyiket feldolgoznank.
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

            correct_image_orientation(filepath)  # ADDED: ez a fuggveny eddig meg volt irva, de sehol nem lett meghivva --
            # emiatt kellett a sablonban kezzel figyelmeztetni a usert, hogy forgassa el a kepet. Most mar automatikus.

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
            # CHANGED: img._getexif() egy nem-publikus metodus volt, a publikus img.getexif()-re cserelve
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

        if img.mode in ("RGBA", "P"):  # ADDED: PNG-k RGBA/paletta modban vannak, JPEG-kent csak RGB-re alakitas utan menthetok el hiba nelkul
            img = img.convert("RGB")

        img.save(image_path, format="JPEG")

def detect_document(path):
    """Detects text and per-word bounding boxes locally using Tesseract OCR.
    CHANGED: korabban ez a fuggveny az OCR.space kulso API-t hivta meg, de a .env-ben az API kulcs
    ures volt, igy minden keres hibaval tert vissza (nem lehetett tudni miert, csendben ures lett
    a valasz). Most helyi Tesseract motorral fut, nincs kulso halozati hivas es nincs kulcskezeles."""
    try:
        with Image.open(path) as img:
            data = pytesseract.image_to_data(img, lang=TESSERACT_LANG, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError:
        log("image_to_text", "CRITICAL", "A Tesseract OCR nincs telepitve / nem talalhato a PATH-on.")
        return {"full_text": "", "boxes": [],
                "error": "A szerveren nincs telepitve a Tesseract OCR (vagy nem talalhato a PATH-on). "
                         "Lasd a telepitesi utmutatot, illetve a TESSERACT_CMD_PATH .env valtozot."}
    except Exception as e:
        log("image_to_text", "ERROR", f"Tesseract OCR hiba a(z) '{path}' fajlon: {e}")
        return {"full_text": "", "boxes": [], "error": f"OCR hiba: {e}"}

    text_annotations_list = []
    full_text_words = []

    for i in range(len(data['text'])):
        word_text = data['text'][i].strip()
        if not word_text:
            continue

        try:
            confidence = float(data['conf'][i])
        except (TypeError, ValueError):
            confidence = -1

        if confidence < 0:  # -1 = Tesseract belso sor/blokk-szintu bejegyzese, nem valodi felismert szo
            continue

        left = data['left'][i]
        top = data['top'][i]
        width = data['width'][i]

        full_text_words.append(word_text)
        text_annotations_list.append({
            'x': int(left + (width / 2)),
            'y': int(top),
            'character': word_text
        })

    full_text = " ".join(full_text_words)

    return {"full_text": full_text, "boxes": text_annotations_list}
