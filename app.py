import csv
import os
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
from geopy.geocoders import Nominatim
import folium
from datetime import datetime
from io import StringIO

# App
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')  # Cambia en producción

# Rutas de archivos (relativas al archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'users.csv')
ADMINS_FILE = os.path.join(BASE_DIR, 'admins.csv')
ATTENDANCE_FILE = os.path.join(BASE_DIR, 'attendance.csv')

# Geolocator, usa user_agent configurable
GEOPY_USER_AGENT = os.environ.get('GEOPY_USER_AGENT', 'asistencia_app')
geolocator = Nominatim(user_agent=GEOPY_USER_AGENT, timeout=10)


# ---------- Helpers ----------
def get_users():
    users = {}
    if not os.path.isfile(USERS_FILE):
        return users
    with open(USERS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row['rut'].strip()] = row['nombre'].strip()
    return users

def get_admins():
    admins = {}
    if not os.path.isfile(ADMINS_FILE):
        return admins
    with open(ADMINS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            admins[row['usuario'].strip()] = row['password'].strip()
    return admins

def get_all_attendance():
    rows = []
    if not os.path.isfile(ATTENDANCE_FILE):
        return rows
    with open(ATTENDANCE_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: v for k, v in row.items()})
    return rows

def get_last_record_type(rut):
    """Devuelve 'entrada' o 'salida' o None si no hay registros."""
    if not os.path.isfile(ATTENDANCE_FILE):
        return None
    last = None
    with open(ATTENDANCE_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('rut') == rut:
                last = row.get('tipo')
    return last

def save_attendance(rut, nombre, address, latitude, longitude, timestamp, tipo):
    file_exists = os.path.isfile(ATTENDANCE_FILE)
    with open(ATTENDANCE_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['rut', 'nombre', 'address', 'latitude', 'longitude', 'timestamp', 'tipo']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'rut': rut,
            'nombre': nombre,
            'address': address,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': timestamp,
            'tipo': tipo
        })

def filter_attendance_by_month(month):
    """month: 'YYYY-MM'"""
    rows = []
    if not os.path.isfile(ATTENDANCE_FILE):
        return rows
    with open(ATTENDANCE_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('timestamp', '').startswith(month):
                rows.append(row)
    return rows

# ---------- Rutas ----------

@app.route('/', methods=['GET', 'POST'])
def index():
    """Vista pública: usuario marca su entrada/salida."""
    users = get_users()
    nombre = None
    map_html = None
    error = None
    record = None

    if request.method == 'POST':
        rut = request.form.get('rut', '').strip()
        address = request.form.get('address', '').strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not rut or not address:
            error = "Complete RUT y dirección."
            return render_template('index.html', error=error)

        nombre = users.get(rut)
        if not nombre:
            error = "RUT no encontrado en la base de datos."
        else:
            try:
                location = geolocator.geocode(address)
            except Exception as e:
                location = None
                error = f"Error al geocodificar: {e}"

            if location:
                latitude = location.latitude
                longitude = location.longitude
                # Generar mapa
                fmap = folium.Map(location=(latitude, longitude), zoom_start=16, tiles='CartoDB positron')
                folium.Marker((latitude, longitude), popup=address, icon=folium.Icon(color='red')).add_to(fmap)
                map_html = fmap._repr_html_()
                # Determinar tipo (entrada/salida)
                last_tipo = get_last_record_type(rut)
                tipo = 'salida' if last_tipo == 'entrada' else 'entrada'
                # Evitar duplicados (dos entradas seguidas o dos salidas seguidas)
                if last_tipo == tipo:
                    error = f"Ya registraste una {tipo}. Debes registrar primero la {'salida' if tipo == 'entrada' else 'entrada'}."
                else:
                    record = {
                        'rut': rut,
                        'nombre': nombre,
                        'address': address,
                        'latitude': latitude,
                        'longitude': longitude,
                        'timestamp': timestamp,
                        'tipo': tipo
                    }
                    save_attendance(rut, nombre, address, latitude, longitude, timestamp, tipo)
            else:
                if not error:
                    error = "Dirección no encontrada. Intenta con otra dirección."

    return render_template('index.html', nombre=nombre, map_html=map_html, error=error, record=record)

# ---------- Admin ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))

    error = None
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '').strip()
        admins = get_admins()
        if admins.get(usuario) and admins.get(usuario) == password:
            session['admin'] = usuario
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Usuario o contraseña incorrectos."
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    users = get_users()
    all_attendance = get_all_attendance()
    meses = set()
    for r in all_attendance:
        ts = r.get('timestamp', '')
        if ts:
            meses.add(ts[:7])
    meses = sorted(list(meses), reverse=True)
    trabajadores = [{"rut": rut, "nombre": nombre} for rut, nombre in users.items()]
    # Si quieres mostrar registros limitados o paginados, ajustar aquí
    return render_template('admin_dashboard.html',
                           trabajadores=trabajadores,
                           meses=meses,
                           all_attendance=all_attendance)

@app.route('/admin/historial')
def admin_historial():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    mes = request.args.get('mes')
    filas = filter_attendance_by_month(mes) if mes else get_all_attendance()
    meses = sorted({r['timestamp'][:7] for r in get_all_attendance()} , reverse=True)
    return render_template('historial.html', filas=filas, meses=meses, mes_seleccionado=mes)

@app.route('/admin/reporte')
def admin_reporte():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    mes = request.args.get('mes')
    filtrados = filter_attendance_by_month(mes) if mes else get_all_attendance()
    output = StringIO()
    fieldnames = ['rut', 'nombre', 'address', 'latitude', 'longitude', 'timestamp', 'tipo']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in filtrados:
        writer.writerow(row)
    output.seek(0)
    filename = f"reporte_asistencia_{mes or 'completo'}.csv"
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)

# ---------- Run ----------
if __name__ == '__main__':
    # Modo desarrollo en local
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)