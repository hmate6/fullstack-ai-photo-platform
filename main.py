from logging import getLogger, ERROR
from app_init import *
from apscheduler.schedulers.background import BackgroundScheduler
from functions.routing import *
from functions.imagetotext import *
from celery import Celery
from flask import render_template
from functions.routes import loading_routes, get_post_routes
from functions import explore
from functions import app_before_request, auth_functions, belepes, emailsendzoho, enhance
from functions import jelszavak_visszaallitasa, regisztralas, rw

celery = Celery(app.name, broker="redis://localhost:6379/0")

scheduler = BackgroundScheduler()

FILE_EXPIRATION_TIME = 3600
temp_folder = "./static/t/"

# REMOVED: ide egy duplikált "/robots.txt" route volt írva ("/robots.txt" néven, hibás vezető '/' -szel a
# fájlnévben). A functions/routes/loading_routes.py-ban van egy helyes, hibátlan verzió ugyanerre az
# útvonalra (robots() függvény), az a route mivel korábban regisztrálódik (lásd a fenti import sort),
# ténylegesen ez futott le mindig -- ez a duplikátum sosem szolgált ki egyetlen kérést sem.
@celery.task
def reset_account_limits():
    with app.app_context():
        if r.exists("running:acc_limits"):
            return 0
        else:
            r.set("running:acc_limits", 1, ex=86400)
        db.session.query(UserAccount).update({
            UserAccount.login_attempts: 0,
            UserAccount.resetpw_attempts: 0
        })
        db.session.commit()

#@celery.task # Kikapcsolva, hogy ne törölje a t mappában lévő elemeket.
def delete_expired_files():
    """ Delete files older than the expiration time. """
    with app.app_context():
        now = datetime.now()
        for filename in os.listdir(temp_folder):
            file_path = os.path.join(temp_folder, filename)
            try:
                if os.path.isfile(file_path):
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if (now - file_creation_time) > timedelta(seconds=FILE_EXPIRATION_TIME):
                        os.remove(file_path)
                        print(f"Deleted file: {filename}")
            except FileNotFoundError:
                print(f"File Not Found Error: {filename}")

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()
    scheduler.add_job(func=delete_expired_files, trigger="interval", minutes=60)
    scheduler.add_job(func=reset_account_limits, trigger="interval", days=7)

logg = getLogger('werkzeug')
logg.setLevel(ERROR)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
