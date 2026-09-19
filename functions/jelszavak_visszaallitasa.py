import secrets

from bleach import clean

from app_init import *
from flask import make_response, request, flash
from functions.auth_functions import *
import bcrypt
from string import ascii_letters, digits
from datetime import timedelta
from time import time
from random import randint  # CHANGED: a nem használt 'choices' import törölve
from functions.emailsendzoho import send_email_new

mode = "pwr"

how_much_seconds = 864000


@app.route("/forgot-password")
def forgot_password_load():
    response = make_response(render_template("auth/forgot_pw.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def jelszo_reset_elkuldve():
    email = clean(request.form.get("email").lower())
    if email == GUEST_EMAIL:
        flash("This is the guest account.")
        return redirect("forgot-password")
    user = UserAccount.query.filter_by(email=email).first()

    if user is None:
        log(mode, "WARNING", f"The e-mail {email} is not registered, password reset link was not sent.")
        flash("User with that email does not exist.")
        return redirect("forgot-password")
    else:
        if user.deleted:
            flash("This account has been deleted and can no longer be accessed. If you believe this is an error, please contact our support team.")
            return redirect("forgot-password")

        if user.acc_version.lower() is not None and user.acc_version.lower() == "google":
            log(mode, "INFO", f"The email is registered with google but user tried to reset password with that account, email: {email}")
            flash('We could not send the password reset request: email is registered with Google!', 'error')
            return redirect("/login")

    if user.resetpw_attempts >= 20:
        log(mode, "WARNING", f"Password reset is blocked account-wise for {email}, password reset link was not sent.")
        flash("Woah! You are sending password reset links too frequently! Take a rest and try again later!")
        return redirect("forgot-password")

    user_id = user.id
    queried_pwr_row = Pwr.query.filter_by(user_id=user_id)
    url = pw_reset_url()

    if queried_pwr_row.first() is None:
        db.session.add(Pwr(user_id=user_id, expire=datetime.now() + timedelta(seconds=how_much_seconds), url=url))
    else:
        queried_pwr_row.update({'expire': datetime.now() + timedelta(seconds=how_much_seconds), 'url': url})

    user.resetpw_attempts += 1
    db.session.commit()
    send_email_new(email, "Reset your password", email_message_for("forgot_password", url, mode))
    flash("pwreset_sent")
    return redirect("/forgot-password")


@app.route("/forgot-password/<url>")
def pwreset_load(url):
    url = Pwr.query.filter_by(url=url).first()

    if url is None or url.expire < datetime.now():
        flash("expired")
        return render_template("auth/forgot_pw_enter_new.html")

    response = make_response(render_template('auth/forgot_pw_enter_new.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'

    return response

@app.route("/forgot-password/<url>", methods=["POST"])
def pwreset(url):
    new_pw = clean(request.form.get("password"))

    if len(new_pw) < 8 or len(new_pw) > 50 :
        log(mode, "WARNING", f"Javascript is turned off, password reset link was not sent.")
        flash("Javascript is turned off.")
        return redirect(f"/forgot-password/{url}")

    try:
        url_from_db = Pwr.query.filter_by(url=url).first()

        # SECOND LEVEL AVAILABILITY CHECK
        if url_from_db is None or url_from_db.expire < datetime.now(): #or UserAccount.query.filter_by(id=url_from_db.user_id).first().deleted:
            flash("expired")
            return redirect(f"/forgot-password/{url}")

        user_id = url_from_db.user_id
        hashed_password = new_password(new_pw)

        email = UserAccount.query.filter_by(id=user_id).first().email

        unix_time = int(time())
        r.set(email, unix_time)

        UserAccount.query.filter_by(id=user_id).update(
            {'password': hashed_password, 'last_pw_reset_unix': unix_time, 'login_attempts': 0, "resetpw_attempts": 0})

        db.session.delete(url_from_db)
        db.session.commit()

    except Exception as e:
        log(mode, "CRITICAL", f"Unexpected error: {e}")
        flash("There was a problem resetting your password.")
        return redirect(f"/forgot-password/{url}")

    flash("after_pwreset")
    return redirect(url_for("belepes_load"))

def new_password(pw):
    salt = bcrypt.gensalt()
    # Hashing Password
    pw_hash = bcrypt.hashpw(
        password=pw.encode(),
        salt=salt)

    return pw_hash.decode()

def pw_reset_url():
    while True:
        generated_url = "".join(secrets.choice(ascii_letters + digits) for x in range(randint(80, 90)))

        if Pwr.query.filter_by(url=generated_url).first() is None:
            break
    return generated_url
