import getpass
from lib.admin.database import db
from lib.admin.models import User, Attempt, Lockout
from lib.admin import validity, const
from lib.admin.bcrypt import bcrypt
import flask_login
import time


def create_user(username, password):
    username = username.lower()

    if User.query.filter_by(username=username).first():
        return 'Account already exists'

    username_resp = validity.check_username(username)
    password_resp = validity.check_password(password)

    if not username_resp['status']:
        return username_resp['msg']

    if not password_resp['status']:
        return password_resp['status']

    pw_hash = bcrypt.generate_password_hash(password).decode()

    user = User(username=username, password=pw_hash)
    attempt = Attempt(user=user)
    lockout = Lockout(user=user)

    db.session.add(user)
    db.session.add(attempt)
    db.session.add(lockout)

    db.session.commit()

    return 'Account created Successfully'


def get_user_input(*, validator, is_password=False):
    data = ''

    while True:

        if not is_password:
            data = input('Enter your username: ')
        else:
            while True:
                data = getpass.getpass('\nEnter your password: ')
                data1 = getpass.getpass('Confirm password: ')

                if data == data1:
                    break

                print('\nError: Passwords do not match')

        resp = validator(data)

        if resp['status']:
            return data

        print(f'\nError: {resp["msg"]}\n')


def authenticate(username, password):
    user = User.query.filter_by(username=username).first()
    resp = {'isAuthenticated': False, 'msg': ''}

    # Check if user exists
    if not user:
        resp['msg'] = 'Account does not exist'
        return resp

    if not user.lockout.is_locked:
        # When it is not locked

        if bcrypt.check_password_hash(user.password, password):
            # When password is correct
            resp['isAuthenticated'] = True
            user.lockout.failed_attempts = 0

            flask_login.login_user(user)
        else:
            # When password is incorrect
            if user.attempt.failed_attempts + 1 >= const.MAX_FAILED_ATTEMPTS:
                resp['msg'] = 'Account locked, try again later'
                user.lockout.time_locked = str(time.time())
                user.lockout.is_locked = True
            else:
                user.attempt.failed_attempts += 1
                resp['msg'] = 'Incorrect password'

        db.session.commit()

    else:
        # When it is locked
        time_locked = float(user.lockout.time_locked)

        if time.time() - time_locked >= const.LOCKOUT_TIME * 60:
            # Lockout expired
            user.lockout.is_locked = False
            user.attempt.failed_attempts = 0
            db.session.commit()
            return authenticate(username, password)
        else:
            resp['msg'] = 'Account locked, try again later'

    return resp
