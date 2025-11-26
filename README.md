```markdown
# Asistencia Georreferenciada - Mejoras

Incluye:
- Geolocalización desde dispositivo (navigator.geolocation).
- Gestión de usuarios desde panel Admin (alta / baja).
- Admin puede cambiar su contraseña (hashed).
- Exportar reportes a Excel (.xlsx).
- Prevención de doble marcaje (evita entradas/salidas seguidas y bloqueo corto).
- Soporte de zona horaria: el navegador envía la zona IANA y los timestamps se guardan en UTC y se muestran convertidos.

Cómo usar
1. Preparar entorno:
   - Python 3.9+
   - Crear virtualenv e instalar dependencias:
     ```
     python -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```

2. Inicializar DB (se crea automáticamente al levantar la app). Un admin por defecto:
   - usuario: admin
   - contraseña: adminpass
   - Cambia la contraseña en el primer login.

3. Ejecutar:
   ```
   python app.py
   ```

4. Rutas principales:
   - `/` : Registro de asistencia (usuarios).
   - `/admin/login` : Login administrador.
   - `/admin` : Panel admin.
   - `/admin/users` : Gestión de usuarios.
   - `/admin/change_password` : Cambiar password admin.
   - `/admin/historial` : Ver historial con filtro por mes.
   - `/admin/reporte` : Exportar a Excel por mes.

Despliegue en Render
1. Subir repo a GitHub.
2. Crear Web Service en Render conectado al repo.
3. Start Command: `gunicorn app:app`
4. Agregar variable de entorno SECRET_KEY con valor seguro.
```