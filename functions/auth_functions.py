from os import path
from uuid import uuid4
# CHANGED: felesleges dupla üres sorok és sorvégi szóközök eltávolítva a fájlban, működés nem változott

from app_init import *
from datetime import datetime

mode = "auth_functions/"
print_log = True

def charge_user(id, amount):
    """CHARGES THE USER AMOUNT OF CREDITS GIVEN."""
    userdb = UserAccount.query.filter_by(id=id).first()
    # if userdb.credits < amount:
    #     return False
    r.set(f"credits:{id}", userdb.credits - amount, ex=1800)
    userdb.credits -= amount
    db.session.commit()
    return True


def temp_filename(extension_with_dot):
    while True:
        uid = uuid4()
        filepath = f"{uid}{extension_with_dot}"
        if not path.isfile(filepath):
            return filepath


def log(mode, level, to_log):
    userip = ""
    userid = session.get("userid", "None")
    email_not_logged_in = session.get("email", "None")

    if not test:
        userip = request.headers['X-Forwarded-For'].split(",")[0]

    current_time = datetime.now()

    response = (f"{current_time} {level.upper()}: "
                f"{to_log} (IP: {userip}), (USERID: {userid}), (EMAIL: {email_not_logged_in})\n\n")

    log_file_path = f"./logs/{mode}.txt"

    with open(log_file_path, mode="a", encoding="UTF-8") as f:
        f.write(response)

    if level.upper() in {"CRITICAL", "ERROR", "FAIL"}:
        error_file_path = f"./logs/errors/{mode}.txt"
        with open(error_file_path, mode="a", encoding="UTF-8") as f:
            f.write(response)

    if print_log:
        print(response)


def ipaddress_cooldown(userip, method):
    if test:
        return 0
    try:
        """Check and update IP address cooldowns using Redis"""

        redis_client = app.config["SESSION_REDIS"]
        key = f"ip:{userip}:{method}"

        count = redis_client.get(key)

        if count is None:
            if method == "homepage_generating":
                redis_client.set(key, 1, ex=21600000)
                log(mode + "ipaddress", "INFO", "New User Homepage generations")
                return 0

            redis_client.set(key, 1, ex=21600)
            log(mode + "ipaddress", "INFO", f"New limit: {method}")
            return 0

        if ipcheck(userip, method) == 1:
            log(mode + "ipaddress", "INFO", f"Too frequent actions for {method}")
            return 1

        redis_client.incr(key)

        return 0

    except Exception as e:
        print(e)


def ipcheck(userip, method):
    if test:
        return 0

    redis_client = app.config["SESSION_REDIS"]
    key = f"ip:{userip}:{method}"

    count = redis_client.get(key)

    if count is None:
        return 0

    count = int(count)

    if method == "register":
        if count > 4:
            log(mode + "ipaddress", "INFO", f"Too frequent registrations! Wait 6 hours.")
            return 1  # render_template("cooldown.html")

    elif method == "homepage_generating":
        if count > 3:
            log(mode + "ipaddress", "INFO", f"Too frequent homepage free generations! Sent to hibernate for 8 months.")
            return 1

    elif method == "pwreset":
        if count > 10:
            log(mode + "ipaddress", "INFO", f"Too frequent password resets.")
            return 1  # render_template("cooldown.html")

    elif method == "login":
        if count > 30:
            log(mode + "ipaddress", "INFO", f"Too frequent logins.")
            return 1  # render_template("cooldown.html")

    elif method == "actions":
        if count > 30:
            log(mode + "ipaddress", "INFO", f"Too frequent actions (feedbacks: contacts and ratings)")
            return 1

    return 0


def email_is_registered(emailaddress):
    if UserAccount.query.filter_by(email=emailaddress).first() is not None: # filter(UserAccount.email.ilike(emailaddress))
        return True
    return False


def user_credits(userid):
    if not logged_in():
        return redirect("/login")
    if not r.exists(f"credits:{userid}"):
        user_queried_credits = UserAccount.query.with_entities(UserAccount.credits).filter_by(id=userid).first().credits
        r.set(f"credits:{userid}", user_queried_credits, ex=1800)

    return int(r.get(f"credits:{userid}"))


def user_plan(userid):
    if not logged_in():
        return "free"
        #return redirect("/login")
    if not r.exists(f"user_plan:{userid}"):
        try:
            queried = UserAccount.query.with_entities(UserAccount.plan).filter_by(id=userid).first()
            if queried is not None:
                plan = queried.plan.lower()
            else:
                return "free"
        except Exception as e:
            log("get_plan", "ERROR", f"Error while checking plan: {e}")
            return "free"

        r.set(f"user_plan:{userid}", plan)

    plan = r.get(f"user_plan:{userid}")
    if not isinstance(plan, str):
        plan = plan.decode("utf-8")

    return plan


def user_status(userid):
    if not logged_in():
        return False
        #return redirect("/login")
    if not r.exists(f"user_status:{userid}"):
        try:
            queried = UserAccount.query.with_entities(UserAccount.email_verified).filter_by(id=userid).first()
            if queried is not None:
                status = str(queried.email_verified).lower()
            else:
                return False
        except Exception as e:
            log("get_plan", "ERROR", f"Error while checking status: {e}")
            return False

        r.set(f"user_status:{userid}", status)

    status = r.get(f"user_status:{userid}")
    if not isinstance(status, str):
        status = status.decode("utf-8")
        if status == "true":
            status = True
        else:
            status = False

    return status

def user_credits_and_plan(userid):
    user_queried = UserAccount.query.with_entities(UserAccount.credits, UserAccount.plan).filter_by(id=userid).first()
    if user_queried is not None:
        return [user_queried.credits, user_queried.plan]
    return None

def query_user_credits_and_verified_status(userid):
    queried_user = UserAccount.query.with_entities(UserAccount.credits, UserAccount.email_verified).filter_by(id=userid).first()
    return [queried_user.credits, queried_user.email_verified]

def check_login_attempts(email):
    return UserAccount.query.filter_by(email=email).first().login_attempts

def too_much_login_attempts(email):
    login_attempts = UserAccount.query.filter_by(email=email).first().login_attempts
    if login_attempts >= 100:
        log(mode + "account_login_attempts", "WARNING", f"{email} got locked out of his account for entering wrong password for 100 times!")
        return True
    return False

def add_failed_login_attempts(email):
    user = UserAccount.query.filter_by(email=email).first()
    user.login_attempts = user.login_attempts + 1
    db.session.commit()
    if test:
        log(mode + "account_login_attempts", "WARNING",
            f"Incorrect login for {email}. Account-Attempts: {user.login_attempts}.")
    else:
        log(mode + "account_login_attempts", "WARNING", f"Incorrect login for {email}. Account-Attempts: {user.login_attempts}, Ip-Attempts: {ipcheck(getip(), "login")}.")


def regex_email(email):
    try:
        email = email[0:email.rfind("@")]
        email = "".join(x for x in email if x.isalnum())
        return email
    except AttributeError:
        return "error"


def email_message_for(type, url, mode=False):
    """Generates message for verification purposes. mode=second level type check if there is a typo in the type argument."""
    domain = HOST if not test_environment else "http://" + localip
    if type == "email_verification" or mode == "register":
        subdomain = "email-verification"
        return f"""
            <html>
                <body style="text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">

                    <h1>E-mail Verification</h1>
                    <p>Click on the button below to verify your email address.</p>
                    <a href="{domain}/{subdomain}/{url}" style="
                        display: inline-block;
                        padding: 10px 20px;
                        font-size: 16px;
                        color: #fff;
                        background-color: #805af5;
                        text-decoration: none;
                        border-radius: 5px;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        font-weight: 600;
                    ">
                        I Confirm My E-mail Address
                    </a>
                    <br><br>
                    <p><b>This link will expire in 24 hours. To request a new verification link, please navigate to <a href="{domain}/settings">{domain}/settings</a> </b></p>
                    <br>
                    <p>If you didn't request the e-mail, then you can ignore it.</p>
                    <br>
                    <p style="font-size: 10px; color: rgb(93, 93, 93)">This is an automated e-mail. To report spam or abuse, contact us on <a href="{domain}/contact">this link.</a> <br>Please don't reply to this e-mail. We won't see your message.</p>
                </body>
            </html>
        """

    elif type == "forgot_password" or mode == "pwr":
        subdomain = "forgot-password"
        return f"""
                    <html>
                        <body style="text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">

                            <h1>Password Reset</h1>
                            <p>To create a new password, click on the button below.</p>
                            <a href="{domain}/{subdomain}/{url}" style="
                                display: inline-block;
                                padding: 10px 20px;
                                font-size: 16px;
                                color: #fff;
                                background-color: #805af5;
                                text-decoration: none;
                                border-radius: 5px;
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                font-weight: 600;
                            ">
                                Reset Password
                            </a>
                            <br><br>
                            <p><b>The link expires in 24 hours.</b></p>
                            <br>
                            <p>If you didn't request the e-mail, then you can ignore it.</p>
                            <br>
                            <p style="font-size: 10px; color: rgb(93, 93, 93)">This is an automated e-mail. To report spam or abuse, contact us on <a href="{domain}/contact">this link.</a> <br>Please don't reply to this e-mail. We won't see your message.</p>
                        </body>
                    </html>
                """

    else:
        raise ValueError("Mistypen error: email_message_for must be 'email_verification' or 'forgot_password'!")
