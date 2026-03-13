from flask import Flask, request, jsonify, session, render_template, make_response, render_template_string
from flask_bcrypt import Bcrypt
from flask_session import Session
from database import get_db_connection, init_db
from cryptography.fernet import Fernet
import os
import re
import time
from collections import defaultdict

app = Flask(__name__)
# Use a static secret key for session persistence if desired, 
# or keep random for high security (but sessions expire on restart)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
Session(app)
bcrypt = Bcrypt(app)

# --- ENCRYPTION SETUP (Option B) ---
# In a real app, store this in a secure environment variable
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # Fallback for dev: static key
    ENCRYPTION_KEY = b'1FujVtfaObZISMSxyRrOTR3k9slUE7x9aXqljvi9pvM='
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher = Fernet(ENCRYPTION_KEY)

def encrypt_data(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(data):
    try:
        return cipher.decrypt(data.encode()).decode()
    except Exception:
        return "[Error de cifrado: Clave incorrecta o datos corruptos]"

# Initialize DB on startup
with app.app_context():
    init_db()

# --- BRUTE FORCE PROTECTION (Rate Limiting) ---
login_attempts = defaultdict(list)

def check_rate_limit(key, limit=5, period=300):
    """Simple rate limit: 5 attempts per 5 minutes per IP/User"""
    now = time.time()
    attempts = [t for t in login_attempts[key] if now - t < period]
    login_attempts[key] = attempts
    if len(attempts) >= limit:
        return False
    login_attempts[key].append(now)
    return True

# --- SECURITY MIDDLEWARE ---
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Adjusted CSP for better security
    response.headers['Content-Security-Policy'] = "default-src 'self' https://cdn.jsdelivr.net; style-src 'self' https://cdn.jsdelivr.net; script-src 'self'; connect-src 'self';"
    return response

@app.before_request
def security_check():
    # Detect manual browser access to API routes (potential attacker)
    # If it's an API route but doesn't have our custom header, it's a trap
    if request.path.startswith('/api/') and request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return log_legacy_audit()

    # CUSTOM CSRF PROTECTION: Require header for POST
    if request.method == "POST":
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return jsonify({"error": "Petición no permitida (Seguridad CSRF)"}), 403

# --- ERROR HANDLING ---
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Petición inválida", "details": str(e.description)}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "No autorizado", "details": "Debes iniciar sesión"}), 401

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Error interno del servidor", "details": "Algo salió mal, intenta más tarde"}), 500

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Acceso denegado"}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- HELPERS ---
def validate_input(text, min_len=1, max_len=1000):
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    return min_len <= len(text) <= max_len

# --- INTERNAL AUDIT SYSTEM ---
@app.route('/admin')
@app.route('/.env')
@app.route('/wp-admin')
@app.route('/phpmyadmin')
@app.route('/config')
@app.route('/.git')
def log_legacy_audit():
    # Obfuscated Easter Egg: Moving content to string and renaming assets
    audit_html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Auditoría del Sistema</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
        <style>
            body { background: #000; color: #ff8000; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; text-align: center; font-family: 'Courier New', monospace; }
            img { max-width: 300px; border: 1px solid #333; margin-bottom: 2rem; box-shadow: 0 0 15px rgba(255, 128, 0, 0.3); }
            .warn { font-size: 2rem; animation: blink 1s infinite; }
            @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <img src="/static/auth_footer_bg.png" alt="Recurso de Auditoría">
        <h1 class="warn">VIOLACIÓN DE ACCESO DETECTADA</h1>
        <p>Tu intento de acceder a rutas sensibles ha sido registrado.</p>
        <p>¡Feliz caza, "hacker"!</p>
        <p><a href="/">Volver a la Zona Segura</a></p>
    </body>
    </html>
    """
    return render_template_string(audit_html), 418

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # Password Validation (INCIBE Standards)
    # 1. Length >= 10
    # 2. Upper and lower case
    # 3. Numbers
    # 4. Special characters (@#$¡*)
    if (len(password) < 10 or 
        not re.search(r'[A-Z]', password) or 
        not re.search(r'[a-z]', password) or 
        not re.search(r'[0-9]', password) or 
        not re.search(r'[@#$¡*]', password)):
        return jsonify({"error": "La contraseña no cumple los requisitos de máxima seguridad (INCIBE)"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
    except Exception:
        return jsonify({"error": "El nombre de usuario ya existe"}), 400
    finally:
        conn.close()
        
    return jsonify({"message": "Usuario registrado correctamente"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "Credenciales incompletas"}), 400
    
    # Rate limit check by IP
    if not check_rate_limit(request.remote_addr):
        return jsonify({"error": "Demasiados intentos. Inténtalo más tarde."}), 429
    
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, password FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and bcrypt.check_password_hash(user['password'], password):
        session.clear() # Prevent session fixation
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({"message": "Sesión iniciada", "username": user['username']})
    
    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Sesión cerrada"})

@app.route('/api/notes', methods=['GET'])
@login_required
def get_notes():
    user_id = session.get('user_id')
    conn = get_db_connection()
    notes = conn.execute('SELECT id, title, content, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    
    # Decrypt contents for display
    results = []
    for note in notes:
        n = dict(note)
        n['content'] = decrypt_data(n['content'])
        results.append(n)
        
    return jsonify(results)

@app.route('/api/notes', methods=['POST'])
@login_required
def add_note():
    user_id = session.get('user_id')
    data = request.json or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    
    if not validate_input(title, 1, 100) or not validate_input(content, 1, 5000):
        return jsonify({"error": "Título o contenido fuera de los límites permitidos"}), 400
        
    # Encrypt content before saving
    encrypted_content = encrypt_data(content)
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)', 
                     (user_id, title, encrypted_content))
        conn.commit()
    except Exception:
        return jsonify({"error": "Error al guardar la nota"}), 500
    finally:
        conn.close()
    
    return jsonify({"message": "Nota añadida correctamente"}), 201

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    user_id = session.get('user_id')
    conn = get_db_connection()
    note = conn.execute('SELECT id FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id)).fetchone()
    if not note:
        conn.close()
        return jsonify({"error": "Nota no encontrada o permiso denegado"}), 404
        
    conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Nota eliminada correctamente"})

if __name__ == '__main__':
    # Never use debug=True in production
    app.run(debug=False, port=5000)
