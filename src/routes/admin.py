from flask import current_app, render_template, request, redirect, url_for, flash
from flask_login import current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_, case, cast, Float, extract
from datetime import datetime, date, timedelta
from calendar import monthrange
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

# --- APROBADORES ---
@admin_bp.route('/admin/aprobadores')
@admin_required
def admin_aprobadores():
    # Optimización N+1
    aprobadores = Aprobador.query.options(
        db.joinedload(Aprobador.usuario),
        db.joinedload(Aprobador.aprobador)
    ).all()
    usuarios = Usuario.query.all()
    return render_template('admin/aprobadores.html', aprobadores=aprobadores, usuarios=usuarios)

@admin_bp.route('/admin/aprobadores/asignar', methods=['POST'])
@admin_required
def admin_asignar_aprobador():
    usuario_id = int(request.form.get('usuario_id'))
    aprobador_id = int(request.form.get('aprobador_id'))
    
    if Aprobador.query.filter_by(usuario_id=usuario_id, aprobador_id=aprobador_id).first():
        flash('Esta relación ya existe', 'warning')
        return redirect(url_for('admin.admin_aprobadores'))
    
    relacion = Aprobador(usuario_id=usuario_id, aprobador_id=aprobador_id)
    db.session.add(relacion)
    db.session.commit()
    flash('Aprobador asignado correctamente', 'success')
    return redirect(url_for('admin.admin_aprobadores'))

@admin_bp.route('/admin/aprobadores/eliminar/<int:id>', methods=['POST'])
@admin_required
def admin_eliminar_aprobador(id):
    aprobador = Aprobador.query.get_or_404(id)
    db.session.delete(aprobador)
    db.session.commit()
    flash('Relación eliminada correctamente', 'success')
    return redirect(url_for('admin.admin_aprobadores'))

# --- FESTIVOS ---
@admin_bp.route('/admin/festivos')
@admin_required
def admin_festivos():
    # Obtener filtro de la URL (default: solo activos)
    mostrar = request.args.get('mostrar', 'activos')
    
    if mostrar == 'todos':
        festivos = Festivo.query.order_by(Festivo.fecha.desc()).all()
    elif mostrar == 'archivados':
        festivos = Festivo.query.filter_by(activo=False).order_by(Festivo.fecha.desc()).all()
    else:  # 'activos' (default)
        festivos = Festivo.query.filter_by(activo=True).order_by(Festivo.fecha.desc()).all()
    
    return render_template('admin/festivos.html', festivos=festivos, mostrar=mostrar)

@admin_bp.route('/admin/festivos/crear', methods=['POST'])
@admin_required
def admin_crear_festivo():
    from src.utils import invalidar_cache_festivos
    
    fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
    descripcion = request.form.get('descripcion')
    
    if Festivo.query.filter_by(fecha=fecha).first():
        flash('Este festivo ya existe', 'warning')
        return redirect(url_for('admin.admin_festivos'))
    
    festivo = Festivo(
        fecha=fecha, 
        descripcion=descripcion,
        activo=True  # ✅ Explícitamente activo
    )
    db.session.add(festivo)
    db.session.commit()
    
    invalidar_cache_festivos()
    
    flash('Festivo añadido correctamente', 'success')
    return redirect(url_for('admin.admin_festivos'))

# Endpoint para archivar/desarchivar
@admin_bp.route('/admin/festivos/toggle/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_festivo(id):
    from src.utils import invalidar_cache_festivos
    
    festivo = Festivo.query.get_or_404(id)
    festivo.activo = not festivo.activo
    db.session.commit()
    
    invalidar_cache_festivos()
    
    estado = "activado" if festivo.activo else "archivado"
    flash(f'Festivo {estado} correctamente', 'success')
    return redirect(url_for('admin.admin_festivos'))

@admin_bp.route('/admin/festivos/eliminar/<int:id>', methods=['POST'])
@admin_required
def admin_eliminar_festivo(id):
    festivo = Festivo.query.get_or_404(id)
    db.session.delete(festivo)
    db.session.commit()
    
    invalidar_cache_festivos()  # ✅ AÑADIR ESTA LÍNEA
    
    flash('Festivo eliminado correctamente', 'success')
    return redirect(url_for('admin.admin_festivos'))

# --- TIPOS DE AUSENCIA ---
@admin_bp.route('/admin/tipos-ausencia', methods=['GET', 'POST'])
@admin_required
def admin_tipos_ausencia():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        try:
            max_dias = int(request.form.get('max_dias'))
        except (ValueError, TypeError):
            max_dias = 365
            
        tipo_dias = request.form.get('tipo_dias', 'naturales')
        descripcion = request.form.get('descripcion', '')
        
        # Validación simple
        if TipoAusencia.query.filter_by(nombre=nombre).first():
            flash('Ya existe un tipo de ausencia con ese nombre', 'danger')
        else:
            nuevo = TipoAusencia(
                nombre=nombre,
                descripcion=descripcion,
                max_dias=max_dias,
                tipo_dias=tipo_dias
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Tipo de ausencia creado', 'success')
        
        return redirect(url_for('admin.admin_tipos_ausencia'))
        
    tipos = TipoAusencia.query.order_by(TipoAusencia.activo.desc(), TipoAusencia.nombre).all()
    return render_template('admin/tipos_ausencia.html', tipos=tipos)

@admin_bp.route('/admin/tipos-ausencia/toggle/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_tipo_ausencia(id):
    tipo = TipoAusencia.query.get_or_404(id)
    tipo.activo = not tipo.activo
    db.session.commit()
    estado = "activado" if tipo.activo else "desactivado"
    tipo_msg = 'success' if tipo.activo else 'warning'
    flash(f'Tipo de ausencia "{tipo.nombre}" {estado}.', tipo_msg)
    return redirect(url_for('admin.admin_tipos_ausencia'))



# --- CSV EXPORT ENDPOINTS ---


@admin_bp.route('/admin/fichajes/export')
@admin_required
def admin_fichajes_export():
    """Export fichajes to CSV with current filters."""
    import io
    import csv
    from flask import Response
    from calendar import monthrange
    
    usuario_id = request.args.get('usuario_id', type=int)
    hoy = date.today()
    mes = request.args.get('mes', hoy.month, type=int)
    anio = request.args.get('anio', hoy.year, type=int)
    
    _, ultimo_dia = monthrange(anio, mes)
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, ultimo_dia)
    
    query = Fichaje.query.filter(
        Fichaje.es_actual == True,
        Fichaje.tipo_accion != 'eliminacion',
        Fichaje.fecha >= fecha_inicio,
        Fichaje.fecha <= fecha_fin
    )
    
    if usuario_id:
        query = query.filter(Fichaje.usuario_id == usuario_id)
    
    fichajes = query.order_by(Fichaje.fecha.desc(), Fichaje.hora_entrada.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Fecha', 'Usuario', 'Email', 'Entrada', 'Salida', 'Pausa (min)', 'Horas'])
    
    for f in fichajes:
        horas = ((f.hora_salida.hour * 60 + f.hora_salida.minute) - 
                 (f.hora_entrada.hour * 60 + f.hora_entrada.minute)) / 60 - (f.pausa / 60)
        writer.writerow([
            f.fecha.strftime('%d/%m/%Y'),
            f.usuario.nombre,
            f.usuario.email,
            f.hora_entrada.strftime('%H:%M'),
            f.hora_salida.strftime('%H:%M'),
            f.pausa,
            f'{horas:.2f}'
        ])
    
    csv_content = '\ufeff' + output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=fichajes_{mes:02d}_{anio}.csv'}
    )



# --- AUDITORÍA UNIFICADA (Fichajes + Ausencias + Impersonation) ---
@admin_bp.route('/admin/auditoria')
@admin_required
def admin_auditoria():
    usuario_nombre = request.args.get('usuario')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    logs_unificados = []

    # 1. AUDITORÍA DE FICHAJES
    # Buscamos: Modificaciones (v>1), Eliminaciones, o Creaciones por admin (editor!=usuario)
    query_fichajes = Fichaje.query.join(Usuario, Fichaje.usuario_id == Usuario.id).filter(
        or_(
            Fichaje.version > 1,
            Fichaje.tipo_accion == 'eliminacion',
            Fichaje.editor_id != Fichaje.usuario_id  # <--- DETECTA CREACIÓN POR ADMIN
        )
    )
    
    if usuario_nombre:
        query_fichajes = query_fichajes.filter(Usuario.nombre.ilike(f'%{usuario_nombre}%'))
    if fecha_inicio:
        query_fichajes = query_fichajes.filter(Fichaje.fecha_creacion >= datetime.strptime(fecha_inicio, '%Y-%m-%d'))
    if fecha_fin:
        fin = datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1)
        query_fichajes = query_fichajes.filter(Fichaje.fecha_creacion < fin)
        
    for f in query_fichajes.all():
        tipo = 'MODIFICACIÓN'
        if f.tipo_accion == 'eliminacion': tipo = 'ELIMINACIÓN'
        elif f.version == 1: tipo = 'CREACIÓN (ADMIN)'
        
        logs_unificados.append({
            'fecha_accion': f.fecha_creacion,
            'tipo_etiqueta': tipo,
            'empleado': f.usuario.nombre,
            'editor': f.editor.nombre if f.editor else 'Sistema',
            'objeto': 'Fichaje',
            'detalle': f"{f.fecha.strftime('%d/%m/%Y')} ({f.hora_entrada.strftime('%H:%M')} - {f.hora_salida.strftime('%H:%M')})",
            'motivo': f.motivo_rectificacion or '-'
        })



    # 3. AUDITORÍA DE BAJAS
    query_bajas = SolicitudBaja.query.join(Usuario, SolicitudBaja.usuario_id == Usuario.id).filter(
        SolicitudBaja.aprobador_id.isnot(None)
    )
    
    if usuario_nombre:
        query_bajas = query_bajas.filter(Usuario.nombre.ilike(f'%{usuario_nombre}%'))

    for b in query_bajas.all():
        delta = (b.fecha_respuesta or b.fecha_solicitud) - b.fecha_solicitud
        es_creacion_directa = delta.total_seconds() < 60
        
        tipo = 'CREACIÓN (ADMIN)' if es_creacion_directa else 'APROBACIÓN/RECHAZO'
        
        logs_unificados.append({
            'fecha_accion': b.fecha_respuesta or b.fecha_solicitud,
            'tipo_etiqueta': tipo,
            'empleado': b.usuario.nombre,
            'editor': b.aprobador.nombre if b.aprobador else 'Admin',
            'objeto': 'Baja/Ausencia',
            'detalle': f"{b.fecha_inicio.strftime('%d/%m')} - {b.fecha_fin.strftime('%d/%m')} ({b.tipo_ausencia.nombre}) [{b.estado.upper()}]",
            'motivo': b.motivo or '-'
        })

    # Ordenar cronológicamente (más reciente arriba)
    logs_unificados.sort(key=lambda x: x['fecha_accion'], reverse=True)
    
    # Renderizamos la plantilla nueva que sabe mostrar esta lista unificada
    return render_template('admin/auditoria.html', logs=logs_unificados)

@admin_bp.route('/admin/admin_fichajes', methods=['GET'])
@admin_required
def admin_fichajes():
    # 1. Obtener filtros de la URL o defaults
    usuario_id = request.args.get('usuario_id', type=int)
    
    hoy = date.today()
    try:
        mes = int(request.args.get('mes', hoy.month))
        anio = int(request.args.get('anio', hoy.year))
    except ValueError:
        mes = hoy.month
        anio = hoy.year
        
    # 2. Calcular rango de fechas
    _, ultimo_dia = monthrange(anio, mes)
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, ultimo_dia)
    
    # 3. Query base
    query = Fichaje.query.filter(
        Fichaje.es_actual == True,
        Fichaje.tipo_accion != 'eliminacion',
        Fichaje.fecha >= fecha_inicio,
        Fichaje.fecha <= fecha_fin
    )
    
    # 4. Aplicar filtro de usuario si está seleccionado
    if usuario_id:
        query = query.filter(Fichaje.usuario_id == usuario_id)
    
    # Ordenar
    query = query.order_by(Fichaje.fecha.desc(), Fichaje.hora_entrada.asc())
    
    # 5. PAGINACIÓN
    page = request.args.get('page', type=int, default=1)
    per_page = 50
    
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # 6. Calcular totales para el resumen rápido (Query Separada)
    total_horas = db.session.query(
        func.sum(
            (
                (extract('hour', Fichaje.hora_salida) * 3600 + 
                 extract('minute', Fichaje.hora_salida) * 60) -
                (extract('hour', Fichaje.hora_entrada) * 3600 + 
                 extract('minute', Fichaje.hora_entrada) * 60)
            ) / 3600.0 - (cast(Fichaje.pausa, Float) / 60.0)
        )
    ).filter(
        Fichaje.es_actual == True,
        Fichaje.tipo_accion != 'eliminacion',
        Fichaje.fecha >= fecha_inicio,
        Fichaje.fecha <= fecha_fin
    )
    
    if usuario_id:
        total_horas = total_horas.filter(Fichaje.usuario_id == usuario_id)
        
    total_horas = total_horas.scalar() or 0
    
    # usuarios = Usuario.query.order_by(Usuario.nombre).all() <-- ELIMINADO
    
    usuario_obj = None
    if usuario_id:
        usuario_obj = Usuario.query.get(usuario_id)
    
    return render_template('/admin/admin_fichajes.html',
                           fichajes=pagination.items,
                           pagination=pagination,
                           # usuarios=usuarios, <-- ELIMINADO
                           usuario_seleccionado=usuario_obj, # Pasamos objeto completo
                           mes_actual=mes,
                           anio_actual=anio,
                           total_horas=total_horas)


