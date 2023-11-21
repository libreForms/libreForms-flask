"""
decorators.py: custom decorator functions

"""

__name__ = "app.decorators"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


from functools import wraps
from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
import datetime
from typing import Union
from app.models import User, db
from app.config import config 

def needs_password_reset(user: User, max_age: Union[int, bool]) -> bool:
    """
    Determine if a user needs a password reset based on the max_age parameter.

    Args:
        user (User): A User object containing the user's information.
        max_age (Union[int, bool]): Maximum password age in days or False to disable password aging.

    Returns:
        bool: True if the user needs a password reset, otherwise False.
    """
    if max_age is False:
        return False

    max_password_age = datetime.timedelta(days=max_age)
    if datetime.datetime.now() - user.last_password_change > max_password_age:
        return True
    
    return False


def required_login_and_password_reset(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Assuming you have a needs_password_reset function and max_age defined
        if needs_password_reset(current_user, config['max_password_age']):
            flash('Your password has expired. Please reset your password.', 'warning')
            return redirect(url_for('auth.change_password'))
        return f(*args, **kwargs)
    return decorated_function
