import flask
import flask_login
from flask import Blueprint
from flask_login import LoginManager

from lib.resp import Resp
from lib.admin import const
from lib.admin import account
from lib.admin.models import User
from lib.admin.database import db
from lib.admin.bcrypt import bcrypt

admin = Blueprint('admin', __name__)
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@admin.route('/', methods=['GET', 'POST'])
def login():
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for('admin.dashboard'))

    if flask.request.method == 'POST':
        resp = {'isAuthenticated': False, 'msg': ''}

        if not ('username' in flask.request.form and 'password' in flask.request.form):
            resp['msg'] = 'Provide all requirements'
            return flask.jsonify(resp)

        # Get username and password from form
        username = flask.escape(
            flask.request.form.get('username').strip().lower())
        password = flask.escape(flask.request.form.get('password'))

        # Make sure username and password aren't empty
        if not len(username) or not len(password):
            resp['msg'] = 'Username and password required'
            return flask.jsonify(resp)

        # Attempt to authenticate
        resp = account.authenticate(username, password)
        return flask.jsonify(resp)

    return flask.render_template('admin/login.html')


@admin.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('admin.login'))


@admin.route('/dashboard')
@flask_login.login_required
def dashboard():
    return flask.render_template('admin/dashboard.html')


@admin.route('/settings')
@admin.route('/settings/account')
@flask_login.login_required
def settings():
    return flask.render_template('admin/settings.html')


@admin.route('/settings/account/update', methods=['POST'])
@flask_login.login_required
def settings_account_update():
    resp = Resp()

    if not (
        'username' in flask.request.form and
        'currentPassword' in flask.request.form and
        'newPassword' in flask.request.form and
            'confirmPassword' in flask.request.form):

        resp.msg = 'Request is incomplete'
        return flask.jsonify(resp.serialize)

    username = flask.escape(flask.request.form.get('username')).strip().lower()
    current_password = flask.escape(
        flask.request.form.get('currentPassword')).strip()
    new_password = flask.escape(flask.request.form.get('newPassword')).strip()
    confirm_password = flask.escape(
        flask.request.form.get('confirmPassword')).strip()

    user = flask_login.current_user

    value = {
        'updates': [],
        'errors': []
    }

    if len(username):
        if len(username) < const.MIN_USERNAME_LENGTH or len(username) > const.MAX_USERNAME_LENGTH:
            value['errors'].append(
                f'Username must be between {const.MIN_USERNAME_LENGTH - 1} and {const.MAX_USERNAME_LENGTH + 1} in length'
            )
        else:
            if user.username == username:
                value['errors'].append('You cannot reuse that username')
            else:
                user.username = username
                value['updates'].append('Username updated')

    if len(current_password) and len(new_password) and len(confirm_password):
        if len(new_password) < const.MIN_PASSWORD_LENGTH or len(new_password) > const.MAX_PASSWORD_LENGTH:
            value['errors'].append(
                f'Password must be between {const.MIN_PASSWORD_LENGTH - 1} and {const.MAX_PASSWORD_LENGTH + 1} in length'
            )
        elif not bcrypt.check_password_hash(user.password, current_password):
            value['errors'].append('Invalid password')
        else:
            if bcrypt.check_password_hash(user.password, new_password):
                value['errors'].append('You cannot reuse that password')
            elif new_password != confirm_password:
                value['errors'].append('Passwords do not match')
            else:
                user.password = bcrypt.generate_password_hash(
                    new_password).decode()
                value['updates'].append('Password updated')

    resp.value = value
    db.session.commit()
    return flask.jsonify(resp.serialize)
