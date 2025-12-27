# 1. Usar una imagen base ligera de Python
FROM python:3.11.14-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requisitos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todo el código de la aplicación
COPY . .

# 5. COPIAR Y DAR PERMISOS AL ENTRYPOINT
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 6. Exponer el puerto
EXPOSE 5000

# 7. ELIMINADA LA LÍNEA: RUN flask init-admin (Esto estaba mal)

# 8. Definir el Entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# 9. El comando por defecto sigue siendo el mismo
CMD ["gunicorn", "-k", "gevent", "-w", "4", "--bind", "0.0.0.0:5000", "app:app"]
