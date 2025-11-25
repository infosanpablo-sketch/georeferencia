# Asistencia Georreferenciada (Flask)

Proyecto simple de registro de asistencia con georreferenciación:
- Usuario: marca entrada/salida con su RUT y dirección.
- Administrador: accede al panel, ve trabajadores y descarga reportes mensuales.
- Guardado en CSV (attendance.csv).

Estructura:
```
asistencia/
├── app.py
├── requirements.txt
├── Procfile
├── users.csv
├── admins.csv
├── attendance.csv  # se crea en el servidor (no es obligatorio subirlo)
├── .gitignore
└── templates/
    ├── base.html
    ├── index.html
    ├── admin_login.html
    ├── admin_dashboard.html
    └── historial.html
```

Requisitos
```
Python 3.8+
```

requirements.txt
- Flask
- geopy
- folium
- gunicorn

Cómo crear ZIP (desde la carpeta `asistencia`):
```bash
# desde la carpeta que contiene los archivos y la carpeta templates
zip -r asistencia.zip . -x "*.pyc" "__pycache__/*"
```

Subir a GitHub (resumen):
```bash
git init
git add .
git commit -m "Initial commit: asistencia georreferenciada"
# crea repo en GitHub y luego:
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

Desplegar en Render
1. Crea cuenta en https://render.com.
2. Crea un nuevo "Web Service" -> elige "Connect a repository" -> selecciona tu repo.
3. Build Command: (vacío o usa pip)
4. Start Command: `gunicorn app:app`
5. En "Environment" agrega una variable:
   - SECRET_KEY = una cadena segura (ej: `SECRETO_MUY_SEGURO`)
   - (Opcional) GEOPY_USER_AGENT = `asistencia_app`
6. Deploy.

Acceso
- Página principal (usuarios): `/`
- Login administrador: `/admin/login`
- Panel admin: `/admin`

Notas
- Nominatim (geopy) tiene límites. Para uso intensivo, usa un servicio con API Key.
- Los CSV están en la ruta del proyecto (`attendance.csv`). Asegúrate de permisos de escritura.
- Cambia la SECRET_KEY en producción.
