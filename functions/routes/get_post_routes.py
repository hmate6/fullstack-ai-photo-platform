import os
import urllib.parse

from bleach import clean
from flask_limiter import RateLimitExceeded
from sqlalchemy import desc, inspect

from app_init import *
from flask import request, flash
from functions.auth_functions import email_message_for, log, ipaddress_cooldown
from functions.emailsendzoho import send_email_new
from functions.regisztralas import email_verification_url

@app.route("/del_account", methods=["POST"])
def del_acc():
    """Everything associated to the user account's will be deleted, except the email address and the registration date.
    Email address will be preserved to prevent re-registration"""
    dbuser = UserAccount.query.filter_by(id=session.get("userid"))
    dbuser.first().deleted = True# Delete account True

    userid = dbuser.first().id

    # delete every likedimage entry
    LikedImage.query.filter_by(user_id=userid).delete(synchronize_session=False)

    user = UserAccount.query.filter_by(id=userid).first()
    if user:
        mapper = inspect(UserAccount)

        for column in mapper.columns:
            col_name = column.name

            # Skip protected fields
            if col_name in ("id", "email", "created_at", "acc_version"):
                continue

            if column.type.python_type is bool:
                setattr(user, col_name, False)

            elif column.type.python_type is int:
                setattr(user, col_name, 0)

            elif column.nullable:
                setattr(user, col_name, None)

            else:
                setattr(user, col_name, "")

        user.login_attempts = 0
        user.resetpw_attempts = 0
        user.deleted = True

    Pwr.query.filter_by(user_id=userid).delete(synchronize_session=False)
    EmailVerification.query.filter_by(email=dbuser.first().email).delete(synchronize_session=False)

    images = Images.query.filter_by(user_id=userid).all()
    filenames = [img.name for img in images]

    Images.query.filter_by(user_id=userid).delete(synchronize_session=False)

    for filename in filenames:
        if not filename:
            continue

        file_path = os.path.join("static/photo/", filename)

        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                os.remove(file_path.replace("static/photo/", "static/photo-hd/"))
            except OSError:
                pass

    db.session.commit()

    r.set(session.get('user'), int(time()))
    session.clear()

    r.delete(f"user_status:{userid}")
    r.delete(f"user_plan:{userid}")
    r.delete(f"credits:{userid}")
    r.delete(dbuser.first().email)
    return redirect("/")

@app.route("/del_image", methods=["DELETE"])
def del_image():
    data = request.get_json()
    image_id = data.get('image_id')
    db.session.expire_all()

    query = Images.query.filter_by(user_id=session.get("userid"), name=image_id).first()
    if query is None or query.deleted:
        return jsonify({"status": 404})

    query.deleted = True
    db.session.commit()
    return jsonify({"status": "success"})


@app.route("/resend_verification_email", methods=["POST"])
@limiter.limit("5/day")
def resend_verification():
    if not logged_in():
        return jsonify({"error": "notloggedin"})
    try:
        url = email_verification_url()
        email = session.get("email")

        account = UserAccount.query.filter_by(email=email).first()

        if account.email_verified:
            return jsonify({"error": "already_verified"})

        if account.verification_limit >= 40:
            return jsonify({"error": "You sent too many requests. Please try again later."})

        try:
            dbrow = EmailVerification.query.filter_by(email=email).first()
            if dbrow is not None:
                dbrow.url = url
                dbrow.expire = datetime.now() + timedelta(hours=72)
            else:
                db.session.add(EmailVerification(email=email, url=url, expire=datetime.now() + timedelta(hours=72)))

            account.verification_limit += 1
            db.session.commit()

            send_email_new(email, "New E-mail Address Verification Link", email_message_for("email_verification", url))
            log("emailsend", "INFO", "Successfully sent verification message again.")
        except Exception as e:
            log("emailsend", "ERROR", f"Unexpected Error while resending verification code! ({e})")

    except RateLimitExceeded as e:
        flash("You sent too many email verification requests. Please try again later.")

    return jsonify({"success": "success"})

@app.route("/contact", methods=["POST"])
@limiter.limit("10 per minute")
def visszajelzes_kuldes():
    try:
        user = int(session.get("userid", 0))
        email = clean(request.form.get("email"))[0:500]
        subject = clean(request.form.get("subject"))[0:100]
        message = clean(request.form.get("message"))[0:4500]
        db.session.add(Feedbacks(userid=user, feedback=message, rating=0, date=datetime.now(), email=email, subject=subject))
        db.session.commit()
        log("contact", "INFO", f"Message successfully saved into the database! {email} {subject}")
        flash("Your message was successfully sent. We are trying to respond to it as fast as we can.")

    except Exception as e:
        log("contact", "ERROR", f"error while contacting: {e}")
        db.session.rollback()
        flash("There was a problem delivering your message. Please try again later.")

    return redirect("/contact")


@app.route('/load-content/<userid>', methods=['GET'])
def load_content(userid):
    if not logged_in():
        return redirect("/login")

    decoded_userid = urllib.parse.unquote(userid)

    if '..' in decoded_userid or decoded_userid.startswith('/') or not decoded_userid.isdigit() or int(
            decoded_userid) != session.get("userid"):
        return jsonify({"security_error": "You can only load YOUR images."})

    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 12))
    except ValueError:
        offset = 0
        limit = 12

    prompts = db.session.query(Images.prompt, Images.name).filter(Images.user_id == userid).order_by(Images.id.desc()).offset(
        offset).limit(limit).all()

    available_items_count = len(prompts)

    items = [{'image': prompts[i][1], 'prompt': prompts[i][0]} for i in range(available_items_count)]

    return jsonify(items)

@app.route('/load-explore-more/<offset>', methods=['GET'])
def load_more_content(offset):
    if not logged_in() or not offset.isdigit():
        return abort(405)

    limit = 12
    ordered_by = clean(request.args.get("ordered_by", "newest"))

    offset = int(offset[0:999999])

    if ordered_by == "most_liked":
        rows = Images.query.filter_by(public=True).order_by(desc(Images.likes)).offset(offset).limit(limit).all()

    else:
        rows = Images.query.filter_by(public=True).order_by(desc(Images.published_at)).offset(offset).limit(limit).all()
    available_items_count = len(rows)

    items = [{
        'image': f"{rows[i].name}",
        'prompt': rows[i].prompt,
        "style": rows[i].stilus,
        "ago": get_how_much_times_ago(int((datetime.now() - rows[i].published_at).total_seconds() / 60)),
        "aspect_ratio": rows[i].arany,
        "likes": rows[i].likes,
        "location_w_id": f"{rows[i].user_id}/{rows[i].name}",
        "location_without": rows[i].name
    } for i in range(available_items_count)]

    return jsonify(items)
