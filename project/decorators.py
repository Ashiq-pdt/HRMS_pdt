from functools import wraps

from flask import flash,redirect,url_for
from flask_login import current_user

def employees_required(f):
    """
    Restrict access from users who have no coins.

    :return: Function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.no_of_employees == 0:
            flash("Sorry, you're plan restricts the number of employees to be added. You should upgrade your plan to add more.",
                  'warning')
            return redirect(url_for('main.employees'))

        return f(*args, **kwargs)

    return decorated_function