from flask import Flask, request, jsonify, session, render_template
from flask_bcrypt import Bcrypt
from flask_session import Session
from database import get_db_connection, init_db
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
bcrypt = Bcrypt(app)

# Initialize DB on startup
with app.app_context():
    init_db()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    print(f"[DEBUG] Registrando usuario: {username}")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print(f"[DEBUG] Usuario {username} registrado correctamente")
    except Exception as e:
        print(f"[DEBUG] Error al registrar: {e}")
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()
        
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    print(f"[DEBUG] Intento de login para: {username}")
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user:
        print(f"[DEBUG] Usuario encontrado en DB. Comprobando hash...")
        if bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            print(f"[DEBUG] Login exitoso para {username}. Session: {session}")
            return jsonify({"message": "Logged in successfully", "username": user['username']})
        else:
            print(f"[DEBUG] Hash de contraseña NO coincide")
    else:
        print(f"[DEBUG] Usuario NO encontrado en la base de datos")
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route('/api/notes', methods=['GET'])
@login_required
def get_notes():
    user_id = session.get('user_id')
    print(f"[DEBUG] Obteniendo notas para user_id: {user_id}")
    
    conn = get_db_connection()
    notes = conn.execute('SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    
    print(f"[DEBUG] Encontradas {len(notes)} notas")
    return jsonify([dict(note) for note in notes])

@app.route('/api/notes', methods=['POST'])
@login_required
def add_note():
    user_id = session.get('user_id')
    data = request.json
    title = data.get('title')
    content = data.get('content')
    
    print(f"[DEBUG] Añadiendo nota para user_id {user_id}: {title}")
    
    if not title or not content:
        return jsonify({"error": "Title and content required"}), 400
        
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)', 
                     (user_id, title, content))
        conn.commit()
        print(f"[DEBUG] Nota guardada correctamente en DB")
    except Exception as e:
        print(f"[DEBUG] Error al guardar nota: {e}")
        return jsonify({"error": "Error interno al guardar"}), 500
    finally:
        conn.close()
    
    return jsonify({"message": "Note added successfully"}), 201

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    conn = get_db_connection()
    # Ensure user owns the note
    note = conn.execute('SELECT * FROM notes WHERE id = ? AND user_id = ?', (note_id, session['user_id'])).fetchone()
    if not note:
        conn.close()
        return jsonify({"error": "Note not found or unauthorized"}), 404
        
    conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Note deleted successfully"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
