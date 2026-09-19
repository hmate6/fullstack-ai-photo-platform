import os
import re

from flask import flash
from werkzeug.utils import send_file, send_from_directory

from app_init import *

@app.route("/static/generated_images/<userid>/<image>/")
def redirect_images(userid, image):
    if not logged_in():
        return redirect(url_for("belepes_load"))

    if not re.match(r'^img_\d+\.jpeg$', image) or not userid.isdigit() or ".." in request.path:
        return abort(404)

    base_directory = os.path.realpath("./static/generated_images")
    target_directory = os.path.realpath(f"./static/generated_images/{userid}/{image}")

    if os.path.commonpath([base_directory, target_directory]) != base_directory:
        return abort(403)

    userid = int(userid)

    if userid != session.get("userid"):
        return abort(404)

    if not os.path.exists(f"./static/generated_images/{userid}/{image}"):
        return abort(404)

    if UserAccount.query.filter_by(id=userid).first().plan == "free":
        return "You are trying to access an image that requires you to have a pro or higher plan! You can upgrade by navigating to the /upgrade page. Note: it's low priced."

    return send_from_directory(f"./static/generated_images/{userid}", image)


# Ez a thumbnail
@app.route("/static/generated_images_thumbnails/<userid>/<image>", strict_slashes=False)
def redirect_images_thumbnails(userid, image):
    image = image.replace("/", "")
    if not re.match(r'^img_\d+\.jpeg$', image):
        return abort(404)

    if not userid.isdigit():
        return abort(404)

    if ".." in request.path:
        return abort(404)

    if not os.path.exists(f"./static/generated_images_thumbnails/{userid}/{image}"):
        return abort(404)

    base_directory = os.path.realpath("./static/generated_images_thumbnails")
    target_directory = os.path.realpath(f"./static/generated_images_thumbnails/{userid}/{image}")

    if os.path.commonpath([base_directory, target_directory]) != base_directory:
        return abort(403)

    queried = Images.query.filter_by(user_id=userid, name=image).first()

    if not queried:
        return abort(404)

    # if public send the image
    if queried.public:
        return send_from_directory(f"./static/generated_images_thumbnails/{userid}", image)

    # if not set public, then determine if the logged in user is the owner of this image and only he/she can access it
    if not logged_in():
        return abort(404)

    userid = int(userid)

    if userid != session.get("userid"):
        return abort(404)

    return send_from_directory(f"./static/generated_images_thumbnails/{userid}", image)

@app.route("/templates/")
def no_access_html_templates():
    return abort(404)

@app.errorhandler(404)
def page_not_found(name):
     return render_template("codes/404.html")

@app.errorhandler(405)
def method_not_allowed(e):
    return f"Are you lost? Method Not Allowed!"

@app.errorhandler(500)
def szervererror(name):
     return render_template("codes/500.html")

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File size exceeds the maximum limit of 20 MB"}), 413

@app.errorhandler(429)
def too_many_requests(e):
    if request.path == "/resend_verification_email" and request.method == "POST":
        return jsonify({"error": "You sent too many requests. Please try again later."})
    elif request.path == "/toggle-like":
        return jsonify({"cooldown": "cooldown"})
    elif request.path == "/index_generate_images" and request.method == 'POST':
        flash("indexgen")
        return {'message': "limit"}
    elif request.path == "/login":
        flash("You tried to login multiple times in a row. Take a rest!")
        return redirect("/login")
    # FIGYELEM (nem módosítva, csak jelölve): ez a második "elif" ág is request.path == "/login"-t
    # néz, ugyanazt, mint a fölötte lévő -- emiatt ez az ág sosem fut le (valószínűleg /signup vagy
    # /register lett volna a szándék). Mivel ez viselkedést érintene, nem változtattam meg, csak jelzem.
    elif request.path == "/register":
        flash("You tried to register multiple times in a row. It's not allowed to create multiple accounts!")
        return redirect("/register")
    elif request.path == "/background-remover" and request.method == "POST":
        flash("You are removing backgrounds from images too frequently! Create an account to remove backgrounds without any limitations!")
        return jsonify({"toorapid": "toorapid"})
    elif request.path == "/contact" and request.method == "POST":
        flash("You are sending messages too frequently! Take a rest!")
        return redirect("/contact")
    else:
        return "<h1>Too many request Error!</h1><br>It seems like you tried to do something too frequently! Take a rest and try again later!", 429