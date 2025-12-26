from flask import current_app, render_template, request, redirect, url_for, flash
from flask_login import current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import or_
from src import db, admin_required
from src.models import Usuario
from . import admin_bp

@admin_bp.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    # MODIFICADO: No cargamos todos los usuarios de golpe para la vista inicial
    # Se obtendrán por AJAX o paginación si fuera necesario
    page = request.args.get('page', 1, type=int)
    usuarios = Usuario.query.paginate(page=page, per_page=20)
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin_bp.route('/admin/api/usuarios/buscar')
@admin_required
def admin_buscar_usuarios():
    """
    Endpoint AJAX para buscar usuarios por nombre/email.
    Retorna JSON para autocompletado typeahead.
    """
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return {'results': []}
    
    # Búsqueda insensible a mayúsculas
    usuarios = Usuario.query.filter(
        or_(
            Usuario.nombre.ilike(f'%{query}%'),
            Usuario.email.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    results = [
        {
            'id': u.id,
            'text': f"{u.nombre} ({u.email})"
        } for u in usuarios
    ]
    
    return {'results': results}

@admin_bp.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def admin_crear_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        rol = request.form.get('rol')

        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('admin.admin_crear_usuario'))
        
        # Crear usuario
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password),
            rol=rol,

        )
        db.session.add(usuario)
        db.session.commit()

        # Log de auditoría
        current_app.logger.info(
            f"Usuario creado: {email}",
            extra={
                "event.action": "user-creation",
                "event.category": ["iam", "configuration"],
                "user.target.email": email,
                "user.target.role": rol,
                "actor.email": current_user.email, # Quién hizo la acción
                "actor.id": current_user.id
            }
        )
        
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('admin.admin_usuarios'))
    
    return render_template('admin/crear_usuario.html')

@admin_bp.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.nombre = request.form.get('nombre')
        usuario.email = request.form.get('email')
        usuario.rol = request.form.get('rol')

        
        password = request.form.get('password')
        if password:
            usuario.password = generate_password_hash(password)

        password = request.form.get('password')
        password_changed = False
        
        if password:
            usuario.password = generate_password_hash(password)
            password_changed = True

        
        db.session.commit()

        # --- LOGGING INICIO ---
        current_app.logger.info(
            f"Usuario editado: {usuario.email}",
            extra={
                "event.action": "user-update",
                "event.category": ["iam", "configuration"],
                "event.module": "admin",
                "user.target.id": usuario.id,
                "user.target.email": usuario.email,
                "user.target.role": usuario.rol,
                "user.changes.password": password_changed, # Info útil de seguridad
                "actor.email": current_user.email,
                "actor.id": current_user.id,
                "source.ip": request.remote_addr
            }
        )
        # --- LOGGING FIN ---
        
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('admin.admin_usuarios'))
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

@admin_bp.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
@admin_required
def admin_eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    # Capture for logging
    target_email = usuario.email
    target_id = usuario.id
    target_role = usuario.rol

    db.session.delete(usuario)
    db.session.commit()

    # --- LOGGING INICIO ---
    current_app.logger.info(
        f"Usuario eliminado: {target_email}",
        extra={
            "event.action": "user-deletion",
            "event.category": ["iam", "configuration"],
            "event.outcome": "success",
            "user.target.id": target_id,
            "user.target.email": target_email,
            "user.target.role": target_role,
            "actor.email": current_user.email,
            "actor.id": current_user.id,
            "source.ip": request.remote_addr
        }
    )
    # --- LOGGING FIN ---
    
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('admin.admin_usuarios'))




