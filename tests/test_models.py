from src.models import Usuario
from src import db
from werkzeug.security import check_password_hash
from datetime import date, time

def test_usuario_password_hashing(test_app, employee_user):
    """Verificar que el hash de contraseña funciona."""
    # employee_user se crea con password 'emp123' en conftest.py
    assert check_password_hash(employee_user.password, 'emp123')
    assert not check_password_hash(employee_user.password, 'wrongpass')

