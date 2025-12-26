from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from src import db
from src.models import Usuario
from . import main_bp

@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@main_bp.before_app_request
def check_admin_password():
    if current_user.is_authenticated and current_user.rol == 'admin':
        # Evitar bucle si ya estamos en perfil intentando cambiarla
        if request.endpoint == 'main.perfil':
            return
            
        default_pass = current_app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD', 'admin123')
        if check_password_hash(current_user.password, default_pass):
            flash('⚠️ Seguridad: Estás usando la contraseña de administrador por defecto. Por favor, cámbiala en tu perfil.', 'warning')

@main_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not check_password_hash(current_user.password, current_password):
            flash('La contraseña actual es incorrecta', 'danger')
            return redirect(url_for('main.perfil'))
        
        if new_password != confirm_password:
            flash('Las contraseñas nuevas no coinciden', 'danger')
            return redirect(url_for('main.perfil'))
        
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('main.perfil'))
        
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Contraseña actualizada correctamente', 'success')
        return redirect(url_for('main.perfil'))
    
    return render_template('perfil.html')