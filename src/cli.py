import click
from flask.cli import with_appcontext
from src import db
from src.models import Usuario

@click.command('import-users')
@click.argument('csv_file', type=click.Path(exists=True))
@with_appcontext
def import_users_command(csv_file):
    """
    Importa usuarios desde un fichero CSV.
    Formato esperado: nombre,email
    """
    import csv
    import secrets
    from werkzeug.security import generate_password_hash
    from datetime import datetime

    db.create_all()  # Ensure tables exist
    print(f"--- Importando usuarios desde {csv_file} ---")
    
    count_new = 0
    count_skip = 0
    anio_actual = datetime.now().year  # ✅ Calcular una vez

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

        if 'email' not in reader.fieldnames or 'nombre' not in reader.fieldnames:
            print("❌ Error: El CSV debe tener columnas 'nombre' y 'email'.")
            return

        for row in reader:
            nombre = row.get('nombre', '').strip()
            email = row.get('email', '').strip()

            if not email:
                continue

            existing = Usuario.query.filter_by(email=email).first()
            if existing:
                print(f"Saltado {email}: Ya existe.")
                count_skip += 1
                continue

            # Crear usuario
            raw_pass = secrets.token_urlsafe(8)
            password_hash = generate_password_hash(raw_pass)

            new_user = Usuario(
                nombre=nombre,
                email=email,
                password=password_hash,
                rol='usuario'
            )
            
            db.session.add(new_user)
            db.session.flush()  # ✅ Genera new_user.id
            
            count_new += 1
            print(f"✅ Creado: {nombre} ({email}) - Pass: {raw_pass}")

    db.session.commit()
    print(f"\nResumen: {count_new} creados, {count_skip} saltados.")


@click.command('init-admin')
@with_appcontext
def init_admin_command():
    """
    Crea el usuario administrador inicial basado en variables de entorno.
    """
    from werkzeug.security import generate_password_hash
    from flask import current_app
    
    db.create_all()  # Ensure tables exist
    
    email = current_app.config.get('DEFAULT_ADMIN_EMAIL')
    password = current_app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD')
    
    if not email or not password:
        print("❌ Error: DEFAULT_ADMIN_EMAIL o DEFAULT_ADMIN_INITIAL_PASSWORD no definidos.")
        return

    existing = Usuario.query.filter_by(email=email).first()
    if existing:
        print(f"ℹ️ El usuario administrador ({email}) ya existe.")
        return

    admin = Usuario(
        nombre='Administrador',
        email=email,
        password=generate_password_hash(password),
        rol='admin'
    )
    db.session.add(admin)
    db.session.commit()
    print(f"✅ Usuario Administrador creado: {email}")
    