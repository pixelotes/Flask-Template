#!/bin/sh
# entrypoint.sh

# Detener el script si hay errores
set -e

# Ejecutar init-admin usando las variables de entorno del momento de ejecución
# Como tu comando en cli.py comprueba si ya existe, es seguro ejecutarlo siempre.
echo "Inicializando administrador..."
flask init-admin

# Ejecutar el comando principal (el CMD del Dockerfile)
# "$@" se sustituye por el comando que viene después (gunicorn...)
exec "$@"
