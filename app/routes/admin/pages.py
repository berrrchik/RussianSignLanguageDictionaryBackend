"""
HTML страницы административной панели.
"""
from flask import Blueprint, render_template

bp = Blueprint('admin_pages', __name__)


@bp.route('/login', methods=['GET'])
def login_page():
    """Страница входа в административную панель."""
    return render_template('login.html')


@bp.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Главная страница административной панели."""
    return render_template('dashboard.html')


@bp.route('/signs', methods=['GET'])
def signs_page():
    """Страница управления жестами."""
    return render_template('signs.html')


@bp.route('/categories', methods=['GET'])
def categories_page():
    """Страница управления категориями."""
    return render_template('categories.html')


@bp.route('/lessons', methods=['GET'])
def lessons_page():
    """Страница управления уроками."""
    return render_template('lessons.html')

