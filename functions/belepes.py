import bcrypt
from flask import make_response, flash
# CHANGED: felesleges dupla üres sorok eltávolítva, működés nem változott
from app_init import *
from functions.auth_functions import *
from bleach import clean
from authlib.integrations.base_client.errors import OAuthError, MismatchingStateError

mode = "login"
# ROUTE
@app.route("/login", methods=['POST'])
@limiter.limit("10 per minute")
def belepes_email():
    if "login_send" in request.form:
        userip = request.headers.get('X-Forwarded-For', request.remote_addr).split(",")[0]

        if ipcheck(userip, "login") == 1: # Ha több mint 30x próbál belépni a felhasználó, akkor az adott IP cím le lesz blokkolva.
            return render_template("cooldown.html")

        redirected = request.args.get("redirect")

        if redirected is not None:
            redirected = clean(redirected)

        email = clean(request.form.get("email").lower())[0:500]

        if not email_is_registered(email):
            log(mode, "INFO", f"Failed to login, e-mail ({email}) is not registered!")
            flash('Wrong email address or password', 'error')
            return redirect("/login")

        accquery = UserAccount.query.filter_by(email=email).first()

        if accquery is not None:
            if accquery.deleted:
                flash("This account has been deleted and can no longer be accessed. If you believe this is an error, please contact our support team.")
                return redirect("/login")

        if check_login_attempts(email) >= 70:
            flash('This account has been locked due to entering the wrong credentials too many times. If you are the owner of this account, create a new password, or contact us for more information.', 'error')
            return redirect("/login")

        pw = clean(request.form.get("password"))

        if len(pw) < 8:
            return "Login failed, please turn on javascript."

        if accquery.acc_version == "google":
            flash("Wrong email address or password")
            return redirect("/login")

        if login_email_pass(email, pw) == 0:  # belépve
            log(mode, "INFO", f"Successful login ({email})")

            accquery.last_login = datetime.now()
            db.session.commit()

            dbitem = accquery
            lastpwreset = accquery.last_pw_reset_unix

            if not r.exists(email):
                r.set(email, accquery.last_pw_reset_unix)

            session["user"] = email
            session["userid"] = dbitem.id
            session["emailregex"] = regex_email(email)
            session["last_pw_reset_unix"] = lastpwreset
            session["email"] = clean(request.form.get("email").lower())
            session["profile_picture"] = dbitem.profile_picture

            if redirected is not None:
                response = redirect(redirected)
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                return response

            return redirect(session.get("reqpath", "/generate"))

        else:
            add_failed_login_attempts(email)
            flash('Wrong email address or password', 'error')  # Flash error message
            if redirected:
                return redirect(f"/login?redirect={redirected}")

            return redirect("/login")
    flash('Wrong email address or password', 'error')  # Flash error message
    return redirect("/login")

def login_email_pass(email, password):
    querydb = UserAccount.query.filter_by(email=email).first()

    if querydb is None:
        return 2  # Not found

    pw_in_db = querydb.password

    check = bcrypt.checkpw(
        password=password.encode(),
        hashed_password=pw_in_db.encode()
        )

    if check:
        return 0  # Valid
    else:
        return 1  # Not valid

@app.route('/continue-w-google')
def login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google_auth.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    try:
        token = google_auth.authorize_access_token()
    except OAuthError as e:
        log(mode, "INFO", f"Oauth error: {e}") # check client secret if problem appears again
        flash('There was a problem signin you in with Google.', 'error')
        return redirect("/login")
    except MismatchingStateError as e:
        log(mode, "INFO", f"CSRF Mismatching State Error: {e}") # check client secret if problem appears again
        flash('There was a problem signin you in with Google, try again!', 'error')
        return redirect("/login")

    user_info = google_auth.get('userinfo').json()

    # Process user_info (e.g., user_info['email'], user_info['name'])
    verified_email = user_info["verified_email"]
    email = user_info["email"].lower()

    profile_picture = user_info["picture"] or None

    if not verified_email:
        log(mode, "INFO", f"The email ({email}) is not verified on Google. Make sure to verify  it before continuing.")
        flash('The e-mail is not verified on Google. Make sure to verify it before continuing.', 'error')
        return redirect("/login")

    accquery = UserAccount.query.filter_by(email=email).first()
    timenow = int(time())
    if accquery is None: # create an account
        db.session.add(UserAccount(email=email, created_at=datetime.now(),
                                   acc_version="google", credits=0,
                                   email_verified=True, profile_picture=profile_picture, last_pw_reset_unix=timenow))
        db.session.commit()
        session["user"] = email
        session["email"] = email
        user = UserAccount.query.filter_by(email=email).first()
        session["userid"] = user.id
        session["profile_picture"] = profile_picture
        session["last_pw_reset_unix"] = timenow

        r.set(email, timenow)
    else: # login
        if accquery.acc_version and accquery.acc_version.lower() != "google":
            log(mode, "INFO", f"Failed to login, e-mail ({email}) is not registered with google but user tried to login with google!")
            flash('An account already exists with that email address, with email-password combination. If you forgot your password, request a new one.', 'error')
            return redirect("/login")
        if accquery.deleted:
            log(mode, "INFO",
                f"Failed to login, e-mail ({email}) is not deleted.")
            flash(
                'Account is deleted and email cannot be reused.',
                'error')
            return redirect("/login")

        accquery.profile_picture = profile_picture

        session["user"] = email
        session["email"] = email
        session["userid"] = accquery.id
        session["profile_picture"] = profile_picture
        session["last_pw_reset_unix"] = accquery.last_pw_reset_unix

        if not r.exists(email):
            r.set(email, accquery.last_pw_reset_unix)

        db.session.commit()

    return redirect("/generate")
