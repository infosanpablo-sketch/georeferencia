import os
import sqlite3
from datetime import datetime, timezone
from io import BytesIO

from flask import (Flask, g, redirect, render_template, request, send_file,
                   session, url_for, flash)
from geopy.geocoders import Nominatim
import folium
from werkzeug.security import check_password_hash, generate_password_hash
from openpyxl import Workbook
try:
    from zoneinfo import ZoneInfo
except Exception:
    from backports.zoneinfo import ZoneInfo  # if using older python with backports

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'asistencia.db')
USERS_CSV = os.path.join(BASE_DIR, 'users.csv')  # optional bootstrap
GEOPY_USER_AGENT = os.environ.get('GEOPY_USER_AGENT', 'asistencia_app')
GEOCODER = Nominatim(user_agent=GEOPY_USER_AGENT, timeout=10)

from flask import Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

#from flask import Flask
#print("Flask.__file__:", Flask.__file__)

#print("Flask class:", Flask)

print("type(app):", type(app))
print("has before_first_request?:", hasattr(app, 'before_first_request'))
print("dir(app) contains before_first_request?:", 'before_first_request' in dir(app))
PY

# --- DB helpers ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        rut TEXT PRIMARY KEY,
        nombre TEXT NOT NULL
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rut TEXT NOT NULL,
        nombre TEXT NOT NULL,
        address TEXT,
        latitude REAL,
        longitude REAL,
        timestamp_utc TEXT NOT NULL,
        tz TEXT,
        tipo TEXT NOT NULL
    )''')
    db.commit()
    # bootstrap admin if none
    cur.execute('SELECT COUNT(*) FROM admins')
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT INTO admins(username, password_hash) VALUES (?,?)',
                    ('admin', generate_password_hash('adminpass')))
        db.commit()
    # bootstrap users from CSV if table empty and CSV exists
    cur.execute('SELECT COUNT(*) FROM users')
    if cur.fetchone()[0] == 0 and os.path.isfile(USERS_CSV):
        import csv
        with open(USERS_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rut = r.get('rut', '').strip()
                nombre = r.get('nombre', '').strip()
                if rut and nombre:
                    try:
                        cur.execute('INSERT INTO users(rut, nombre) VALUES (?,?)', (rut, nombre))
                    except sqlite3.IntegrityError:
                        pass
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Utility functions ---
def get_user_name(rut):
    db = get_db()
    cur = db.execute('SELECT nombre FROM users WHERE rut = ?', (rut,))
    row = cur.fetchone()
    return row['nombre'] if row else None

def add_user_db(rut, nombre):
    db = get_db()
    db.execute('INSERT OR REPLACE INTO users(rut,nombre) VALUES (?,?)', (rut, nombre))
    db.commit()

def delete_user_db(rut):
    db = get_db()
    db.execute('DELETE FROM users WHERE rut = ?', (rut,))
    db.commit()

def list_users_db():
    db = get_db()
    cur = db.execute('SELECT rut, nombre FROM users ORDER BY nombre')
    return cur.fetchall()

def get_last_attendance(rut):
    db = get_db()
    cur = db.execute('SELECT * FROM attendance WHERE rut = ? ORDER BY id DESC LIMIT 1', (rut,))
    return cur.fetchone()

def save_attendance_db(rut, nombre, address, lat, lon, timestamp_utc, tz, tipo):
    db = get_db()
    db.execute('''
        INSERT INTO attendance(rut,nombre,address,latitude,longitude,timestamp_utc,tz,tipo)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (rut, nombre, address, lat, lon, timestamp_utc, tz, tipo))
    db.commit()

def list_attendance(month=None):
    db = get_db()
    if month:
        cur = db.execute("SELECT * FROM attendance WHERE substr(timestamp_utc,1,7)=? ORDER BY timestamp_utc DESC", (month,))
    else:
        cur = db.execute("SELECT * FROM attendance ORDER BY timestamp_utc DESC")
    return cur.fetchall()

def query_admin(username):
    db = get_db()
    cur = db.execute('SELECT * FROM admins WHERE username = ?', (username,))
    return cur.fetchone()

def set_admin_password(username, new_password):
    db = get_db()
    db.execute('UPDATE admins SET password_hash = ? WHERE username = ?', (generate_password_hash(new_password), username))
    db.commit()

# --- Routes ---
@app.before_first_request
def setup():
    init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    record = None
    map_html = None
    users = list_users_db()
    if request.method == 'POST':
        rut = request.form.get('rut', '').strip()
        # prefer coordinates from device
        lat = request.form.get('latitude', '').strip()
        lon = request.form.get('longitude', '').strip()
        tz = request.form.get('tz', '').strip() or None
        address = request.form.get('address', '').strip() or None
        now_utc = datetime.now(timezone.utc)
        # validations
        if not rut:
            error = "RUT requerido."
            return render_template('index.html', error=error, users=users)
        nombre = get_user_name(rut)
        if not nombre:
            error = "RUT no encontrado."
            return render_template('index.html', error=error, users=users)
        # geocode if no coords
        lat_val = None
        lon_val = None
        if lat and lon:
            try:
                lat_val = float(lat); lon_val = float(lon)
            except ValueError:
                lat_val = lon_val = None
        if lat_val is None or lon_val is None:
            if address:
                try:
                    loc = GEOCODER.geocode(address)
                    if loc:
                        lat_val = loc.latitude; lon_val = loc.longitude
                    else:
                        error = "Dirección no encontrada."
                except Exception as e:
                    error = f"Error geocodificando: {e}"
            else:
                error = "Permite geolocalización o ingresa una dirección."
        if error:
            return render_template('index.html', error=error, users=users)
        # determine tipo and prevent double marking
        last = get_last_attendance(rut)
        last_tipo = last['tipo'] if last else None
        tipo = 'salida' if last_tipo == 'entrada' else 'entrada'
        # prevent same tipo twice
        if last_tipo == tipo:
            error = f"Ya existe una marcación de tipo '{tipo}'. Debes alternar entrada/salida."
            return render_template('index.html', error=error, users=users)
        # prevent very rapid duplicate (within 30 seconds)
        if last:
            last_ts = datetime.fromisoformat(last['timestamp_utc'])
            if (now_utc - last_ts).total_seconds() < 30:
                error = "Acción muy rápida. Espera antes de intentar marcar nuevamente."
                return render_template('index.html', error=error, users=users)
        # save
        save_attendance_db(rut, nombre, address or '', lat_val, lon_val, now_utc.isoformat(), tz, tipo)
        # build map
        fmap = folium.Map(location=(lat_val, lon_val), zoom_start=16, tiles='CartoDB positron')
        folium.Marker((lat_val, lon_val), popup=address or f"{lat_val},{lon_val}", icon=folium.Icon(color='red')).add_to(fmap)
        map_html = fmap._repr_html_()
        record = {'rut': rut, 'nombre': nombre, 'address': address or '', 'latitude': lat_val, 'longitude': lon_val, 'timestamp': now_utc.isoformat(), 'tipo': tipo, 'tz': tz}
        return render_template('index.html', record=record, map_html=map_html, users=users)
    return render_template('index.html', users=users)

# --- Admin auth ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        user = request.form.get('usuario', '').strip()
        pwd = request.form.get('password', '').strip()
        row = query_admin(user)
        if row and check_password_hash(row['password_hash'], pwd):
            session['admin'] = user
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Credenciales inválidas."
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    users = list_users_db()
    recent = list_attendance()[:200]
    meses = sorted({r['timestamp_utc'][:7] for r in list_attendance()}, reverse=True)
    return render_template('admin_dashboard.html', trabajadores=users, all_attendance=recent, meses=meses)

# --- User management ---
@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    error = None
    if request.method == 'POST':
        rut = request.form.get('rut', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not rut or not nombre:
            error = "RUT y nombre requeridos."
        else:
            add_user_db(rut, nombre)
            flash('Usuario guardado.', 'success')
            return redirect(url_for('admin_users'))
    users = list_users_db()
    return render_template('admin_users.html', users=users, error=error)

@app.route('/admin/users/delete/<rut>', methods=['POST'])
def admin_users_delete(rut):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    delete_user_db(rut)
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('admin_users'))

# --- Change admin password ---
@app.route('/admin/change_password', methods=['GET', 'POST'])
def admin_change_password():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    error = None
    if request.method == 'POST':
        current = request.form.get('current', '')
        newpwd = request.form.get('new', '')
        confirm = request.form.get('confirm', '')
        row = query_admin(session['admin'])
        if not row or not check_password_hash(row['password_hash'], current):
            error = "Contraseña actual incorrecta."
        elif newpwd != confirm or not newpwd:
            error = "La nueva contraseña y su confirmación no coinciden o están vacías."
        else:
            set_admin_password(session['admin'], newpwd)
            flash('Contraseña cambiada.', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_change_password.html', error=error)

# --- Historial and reports ---
@app.route('/admin/historial')
def admin_historial():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    mes = request.args.get('mes')
    filas = list_attendance(mes) if mes else list_attendance()
    meses = sorted({r['timestamp_utc'][:7] for r in list_attendance()}, reverse=True)
    # convert UTC to local tz for display if tz present
    display_rows = []
    for r in filas:
        ts_utc = datetime.fromisoformat(r['timestamp_utc'])
        tzname = r['tz'] or 'UTC'
        try:
            local = ts_utc.astimezone(ZoneInfo(tzname))
            disp_ts = local.strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception:
            disp_ts = ts_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        display_rows.append({**r, 'display_ts': disp_ts})
    return render_template('historial.html', filas=display_rows, meses=meses, mes_seleccionado=mes)

@app.route('/admin/reporte')
def admin_reporte():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    mes = request.args.get('mes')
    filas = list_attendance(mes) if mes else list_attendance()
    # create excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Asistencia"
    headers = ['RUT', 'Nombre', 'Dirección', 'Latitud', 'Longitud', 'Timestamp UTC', 'Timezone', 'Tipo']
    ws.append(headers)
    for r in filas:
        ws.append([r['rut'], r['nombre'], r['address'], r['latitude'], r['longitude'], r['timestamp_utc'], r['tz'] or '', r['tipo']])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = f"reporte_asistencia_{mes or 'completo'}.xlsx"
    return send_file(bio, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- Status for diagnostics ---
@app.route('/status')
def status():
    ok = os.path.isfile(DB_PATH)
    return {
        'ok': ok,
        'db': DB_PATH,
        'attendance_table_exists': True
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
