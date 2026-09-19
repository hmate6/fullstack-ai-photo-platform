import re
import secrets
from time import time

from bleach import clean

from app_init import *
from flask import g, flash
from functions.auth_functions import user_credits, query_user_credits_and_verified_status, log, user_credits_and_plan, \
    user_plan, user_status

def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        elapsed_time = end_time - start_time
        if not request.path.startswith("/static"):
            log("requests", "INFO", f"({datetime.now()}) ({getip()}) Route {request.path} took {elapsed_time:.4f} seconds to run. user agent: ({request.headers.get('User-Agent')}), referer: ({request.headers.get('Referer')})")
        return result
    return wrapper


@app.before_request
def check_protected():
    if session.get("csrf_token", None) is None:
        session["csrf_token"] = secrets.token_hex(32)
    if request.path.startswith("/static/generated"):
        clean_path = re.sub(r'/+', '/', request.path).strip()
        if clean_path != request.path:
            return redirect(clean_path, code=301)

    if not request.path.startswith("/static"):
        if request.method == "POST" and request.path != "/cookie-accept":
            csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if csrf_token is None or not csrf_token:
                if request.path != "/stripe-webhookom-kesobb":
                    print(request.path, "NO CSRF TOKEN SENT")
                    return "Error: No CSRF Token sent."
            if csrf_token != session.get("csrf_token"):
                print(csrf_token, session.get("csrf_token"))
                if request.path != "/stripe-webhookom-kesobb":
                    print(request.path, "CSRF TOKEN ERRROR!")
                    return "CSRFTOKEN error"
        if logged_in(): # ONLY CHEKS IF USER IN SESSION
            # CHECKS GLOBALLY IF PW WAS RESET, AND IF IT WAS, THEN LOG OUT EVERYONE
            if "last_pw_reset_unix" in session:
                keypair = r.get(session.get("user")).decode()  # user contains the email
                if not keypair:
                    keypair=999999999999
                if int(keypair) > int(session["last_pw_reset_unix"]):
                    session.clear()

            if request.path in {"/login", "/signup", "/sign-up"}:
                return redirect("/generate")

            g.credits = user_credits(session.get("userid"))
            g.status = user_status(session.get("userid"))

            if request.path in {"/generate", "/image-to-text", "/upgrade", "/explore", "/frame-extractor", "/background-remover", "/3d-generate", "/enhance", "/settings"} and not g.status:
                return redirect("/verify-your-email")

            plan = user_plan(session.get("userid"))
            if plan == "free":
                g.maxcredits = 50 #tool uses
            elif plan == "pro":
                g.maxcredits = 500
            elif plan == "plus":
                g.maxcredits = 5000
            else:
                g.maxcredits = 0

            g.profile_picture = session.get("profile_picture", None)

            g.plan = plan
            g.logged_in = True

        else:
            redirect_arg = request.args.get("redirect")

            if redirect_arg is not None:
                redirect_arg = clean(redirect_arg)
                if redirect_arg[1::] not in {"settings", "image-to-text", "generate", "3d-generate", "enhance", "background-remover"}:
                    return redirect("/login")

@app.context_processor
def inject_var():
    if not request.path.startswith("/static"):
        if logged_in():
            return dict(credits = g.credits, user_plan = g.plan, logged_in = g.logged_in, status = g.status,
                        uses = g.maxcredits, HOST=HOST, profile_picture=g.profile_picture)
        else:
            return dict(credits = 0, user_plan = "free", logged_in = False, HOST=HOST)
    return {}

