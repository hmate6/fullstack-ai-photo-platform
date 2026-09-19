import secrets

import requests
from bleach import clean
from flask import make_response, flash

from app_init import *
from functions.auth_functions import log, ipaddress_cooldown, email_message_for
import bcrypt
from sqlalchemy.exc import IntegrityError
from random import randint
from string import ascii_letters, digits
from functions.emailsendzoho import send_email_new
import string

mode = "register"
USER_CREDITS_GRANTED_ON_REGISTER = 0
USER_PLAN_GRANTED_ON_REGISTER = "pro"

def email_verification_link_doesnt_exists(url):
    return EmailVerification.query.filter_by(url=url).first() is None

# MIT TEGYEN, HA:
@app.route("/signup")
def fiok_letrehozasa_load():
    response = make_response(render_template("auth/regisztralas.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'

    return response


@app.route("/signup", methods=['POST'])
@limiter.limit("20 per day")
def fiok_letrehozasa():
    email = clean(request.form.get("email").lower())[0:320]

    wants_email_promotions = False
    if "email_news_subscribe" in request.form:
        wants_email_promotions = clean(request.form.get("email_news_subscribe").lower())[0:7]

        if not wants_email_promotions in {"true", "false"}:
            wants_email_promotions = "false"

        if wants_email_promotions == "true":
            wants_email_promotions = True
        else:
            wants_email_promotions = False

    log(mode, "INFO", f"Tried to register: {email}.")
    #flash("For testing purposes registration is currently disabled. Please wait a few days and come back to check us! :)", "error")
    #return redirect("/signup")

    try:
        """if environ.get("CLOUDFLARE_SECRET_KEY", "") != "":
            token = request.form.get('turnstileToken')
            if not token:
                log(mode, "ERROR", f"Missing turnstile token on registration (Token provided: {token}")
                flash(
                    "Missing turnstile token",
                    'error')  # Flash error message
                return redirect("/signup")

            verification_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
            payload = {
                "secret": environ.get("CLOUDFLARE_SECRET_KEY"),
                "response": token,
                "remoteip": request.remote_addr
            }
            response = requests.post(verification_url, data=payload)
            result = response.json()

            if not result.get("success"):
                log(mode, "ERROR", f"There was a problem verifying if the user is human on registration (Token provided: {token}")
                flash(
                    "There was a problem verifying that you are a human.",
                    'error')  # Flash error message
                return redirect("/signup")"""

        """try:
            email_is_disposable = requests.get(f"https://disposable.debounce.io/?email={email}", timeout=6).json()["disposable"]
            email_is_disposable = "f"
            print("checking dispobale")
            if email_is_disposable == "true":
                flash("You must not use disposable emails.", "error")
                #flash("Don't abuse the free credits. If you like our service, you should create an account using your real e-mail address, just like everyone else. You must not use disposable e-mails. If you think this is a misunderstanding, and this is your real e-mail, contact us.", 'error')  # Flash error message
                return redirect("/signup")
        except requests.exceptions.Timeout:
            print("Couldn't check the disposable")
            pass """
    except Exception as e:
        log(mode, "ERROR", f"Error while turnstile token or checking if e-mail is disposable: {e}")

    pw = clean(request.form.get("password"))

    # PASSWORD CHECKS
    if len(pw) < 8 or len(pw) > 50:
        flash('Password must be at least 8 characters and maximum 50 characters long!', 'error')  # Flash error message
        return redirect("/signup")

    if not validate_password(pw):
        flash("Please include lowercase, uppercase, special characters and numbers in your password!")
        return redirect("/signup")

    # CHECK IF THERE IS ALREADY AN ACCOUNT WITH THE E-MAIL ADDRESS
    queried = UserAccount.query.filter_by(email=email).first()
    if queried is not None:
        if queried.deleted:
            log(mode, "INFO", f"There is a deleted account with {email} email.")
            flash("This email address is linked to a previously deleted account and cannot be used to register a new account. If you believe this is an error or need further assistance, please contact our support team.", "error")
            return redirect("/signup")
        else:
            log(mode, "INFO", f"The e-mail: {email} already has an account registered.")
            flash("An account is already registered with that email address!", "error")
            return redirect("/signup")

    if r.exists(f"already-registered-twice:{getip()}") and int(r.get(f"already-registered-twice:{getip()}")) > 4:
        flash("Slow down, you created too many accounts!", "error")
        return redirect("/signup")

    # PROCESS START
    try:
        salt = bcrypt.gensalt()

        pw_hash = bcrypt.hashpw(
            password=pw.encode(),
            salt=salt)

        timenow = int(time())
        # ADD TO DATABASE HANDLING
        try:
            db.session.add(UserAccount(email=email, password=pw_hash.decode(), created_at=datetime.now(), wants_email_promotions=wants_email_promotions, acc_version="email", last_pw_reset_unix=timenow))
            db.session.commit()

            if r.exists(f"already-registered-twice:{getip()}"):
                r.set(f"already-registered-twice:{getip()}", 2, ex=r.ttl(f"already-registered-twice:{getip()}"))
            else:
                r.set(f"already-registered-twice:{getip()}", 1, ex=160000)

            log(mode, "INFO", f"The e-mail: {email} successfully registered to the website. ")
            #send_email_notification("Új regisztrálás!", f"{email} regisztrált a weboldalra ekkor: {datetime.now()}")
        except IntegrityError:
            log(mode, "INFO", f"E-mail address ({email}) is already in the database") #log(mode, "INFO", f"The e-mail: {email} already has an account registered.")
            flash("An account is already registered with that email address!", "error")
            db.session.rollback()
            return redirect("/signup")
        except Exception as e:
            log(mode, "ERROR", f"Couldn't create the account's database entry. {e}")
            flash("Woah! It's not usual, but we ran into an unexpected error. Please try again!")
            db.session.rollback()
            return redirect("/signup")

        # VERIFICATION URL
        url = email_verification_url()
        db.session.add(EmailVerification(email=email, url=url, expire=datetime.now() + timedelta(hours=72)))
        db.session.commit()

        #r.set(f"verify_email:{session.get('userid')}", "", ex=20)
        #send_email_new(email, "Confirm Your E-mail Address!", email_message_for("email_verification", url, mode))

        # SET SESSION
        session["user"] = email
        session["email"] = email

        r.set(email, timenow)
        session["last_pw_reset_unix"] = timenow


        user = UserAccount.query.filter_by(email=email).first()
        session["userid"] = user.id

        if request.args.get("redirect") is not None and request.args.get("redirect") in ["/generate", "/image-to-text", "/enhance", "/background-remover", "/3d-generate", "/settings", "/frame-extractor"]:
            return redirect(request.args.get("redirect"))
        return redirect("/generate")

    except Exception as e:
        log(mode, "CRITICAL", f"Unknown error: {e}")
        flash("Woah! It's not usual, but we ran into an unexpected error. Please try again, or contact us!")
        return redirect("/signup")

def email_verification_url():
    while True:
        newurl = "".join(secrets.choice(ascii_letters + digits) for x in range(randint(70, 90)))

        if email_verification_link_doesnt_exists(newurl):
            break
    return newurl

@app.route("/email-verification/<name>") # <name><userid> userid confirmation
def regisztracio_megerositese_load(name):
    if email_verification_link_doesnt_exists(name):
        return abort(404)

    user = EmailVerification.query.filter_by(url=name).first()
    email = user.email
    is_expired = user.is_expired
    is_expired_datetime = datetime.now() > user.expire

    if email_verification_link_doesnt_exists(name):
        return abort(404)

    if is_expired or is_expired_datetime:
        return abort(404)

    try:
        db.session.delete(user)
        querieduser = UserAccount.query.filter_by(email=email).first()
        querieduser.email_verified = True
        querieduser.credits = USER_CREDITS_GRANTED_ON_REGISTER
        r.set(f"credits:{querieduser.id}", USER_CREDITS_GRANTED_ON_REGISTER)
        r.set(f"user_plan:{querieduser.id}", USER_PLAN_GRANTED_ON_REGISTER, ex=1800)
        r.set(f"user_status:{querieduser.id}", "true", ex=1800)
        #r.set(f"verificated:{querieduser.id}", True)
        db.session.commit()
        session["status"] = True
        log(mode, "INFO", f"E-mail address successfully veryfied.")
        # send_email_notification("E-mail megerősitve!", f"{email} Megerősitve: {datetime.now()}")
    except IntegrityError:
        db.session.rollback()
        log(mode, "INFO", f"E-mail address integrity error.")
        return abort(404)
    except Exception as e:
        db.session.rollback()
        log(mode, "INFO", f"An error occurred when verifying the e-mail address: {e}. (LOCATION: on e-mail verification page).")
        return abort(404)

    flash("successfully_activated")
    return redirect("/login")

def validate_password(password):
    return (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in string.punctuation for c in password))