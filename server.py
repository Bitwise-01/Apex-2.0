import os
import flask
import flask_login

import lib.utils as utils
from lib.admin import account
from lib.admin.database import db
from lib.admin.bcrypt import bcrypt
from lib.admin import validity, const
from lib.admin.admin import admin, login_manager

from lib.eviltwin.eviltwin import eviltwin
from lib.interface.interface import interface
from lib.handshake.handshake import handshake
from lib.interface.backend import InterfaceBackend
from lib.accesspoints.accesspoints import accesspoints


app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{const.database_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = os.urandom(0x200)
app.config["JSON_SORT_KEYS"] = False

# Register blueprints
admin_url_prefix = utils.gen_admin_url_prefix()
app.register_blueprint(admin, url_prefix=f"/{admin_url_prefix}")
app.register_blueprint(eviltwin, url_prefix="/eviltwin")
app.register_blueprint(interface, url_prefix="/interface")
app.register_blueprint(handshake, url_prefix="/handshake")
app.register_blueprint(accesspoints, url_prefix="/accesspoints")

# Made for reverse engineers
app.register_blueprint(eviltwin, url_prefix="/api/v1/router")

# Bcrypt
bcrypt.init_app(app)

# Login Manager
login_manager.init_app(app)
login_manager.login_view = "/"

# Database
db.app = app
db.init_app(app)

# Create config
utils.create_js_config_file(admin_url_prefix)

# Account
if not os.path.exists(const.database_path):
    db_dirname = os.path.dirname(const.database_path)

    if db_dirname and not os.path.exists(db_dirname):
        os.makedirs(db_dirname)

    # create admin account here
    print("You must create an account")

    username = account.get_user_input(validator=validity.check_username)
    password = account.get_user_input(
        validator=validity.check_password, is_password=True
    )

    # initialize the database
    db.create_all()
    print(account.create_user(username, password))


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


@app.route("/")
def index():
    if flask_login.current_user.is_authenticated:
        # Admin should not be able to see view page
        return flask.redirect(flask.url_for("admin.dashboard"))
    return flask.render_template("index.html")


@app.route("/", methods=["GET", "POST"], defaults={"path": ""})
@app.route("/<path:path>", methods=["GET", "POST"])
def fallback(path):
    return flask.redirect(flask.url_for("index"))


def init_proc():
    """Process to run at run time"""

    utils.kill_all()
    utils.stop_services()
    InterfaceBackend.disable_interfaces()


if __name__ == "__main__":
    print(f"\nDashboard: http://localhost/{admin_url_prefix}\n")

    init_proc()
    app.run(host="0.0.0.0", port=80, debug=False)
