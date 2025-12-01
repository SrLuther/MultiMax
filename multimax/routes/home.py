from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

bp = Blueprint('home', __name__, url_prefix='/home')

@bp.route('/', strict_slashes=False)
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return render_template('home.html', active_page='home')
