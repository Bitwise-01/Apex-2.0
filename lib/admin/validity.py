import re
from lib.admin import const


def check_username(username):
    username = username.strip()
    resp = {'status': 0, 'msg': ''}

    if len(username) == 0:
        return resp

    if len(username) < const.MIN_USERNAME_LENGTH:
        resp['msg'] = f'Username must contain at least {const.MIN_USERNAME_LENGTH} characters'
        return resp
    elif len(username) > const.MAX_USERNAME_LENGTH:
        resp['msg'] = f'Username must contain at most {const.MAX_USERNAME_LENGTH} characters'
        return resp

    if re.findall(r'\W', username):
        resp['msg'] = 'Username must not contain a special or space character'
        return resp

    resp['status'] = 1
    return resp


def check_password(password):
    _password = password
    password = password.strip()
    resp = {'status': 0, 'msg': ''}

    if len(password) == 0:
        return resp

    # Length

    if len(password) < const.MIN_PASSWORD_LENGTH:
        resp['msg'] = f'Password must contain at least {const.MIN_PASSWORD_LENGTH} characters'
        return resp

    elif len(password) > const.MAX_PASSWORD_LENGTH:
        resp['msg'] = f'Password must contain at most {const.MAX_PASSWORD_LENGTH} characters'
        return resp

    # Diversity

    if re.findall(r'^\d+\d$', password):
        resp['msg'] = 'Password must not only consist of numbers'
        return resp

    if not re.findall(r'\d', password):
        resp['msg'] = 'Password must contain a number'
        return resp

    if not re.findall(r'\w', password):
        resp['msg'] = 'Password must contain a letter'
        return resp

    resp['status'] = 1
    return resp
