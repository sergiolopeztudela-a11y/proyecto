document.addEventListener('DOMContentLoaded', () => {
    const authSection = document.getElementById('auth-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const notesList = document.getElementById('notes-list');
    const navActions = document.getElementById('nav-actions');

    const checkAuth = () => {
        // En una app real usaríamos un endpoint de 'me' o similar
        // Pero para este ejemplo, si hay un nombre de usuario en sessionStorage, asumimos logueado
        const username = sessionStorage.getItem('username');
        if (username) {
            showDashboard(username);
        } else {
            showAuth();
        }
    };

    const showDashboard = (username) => {
        authSection.style.display = 'none';
        dashboardSection.style.display = 'block';
        navActions.innerHTML = `
            <li>Hola, <strong>${username}</strong></li>
            <li><a href="#" id="logout-btn" role="button" class="outline secondary">Salir</a></li>
        `;
        document.getElementById('logout-btn').addEventListener('click', logout);
        loadNotes();
    };

    const showAuth = () => {
        authSection.style.display = 'block';
        dashboardSection.style.display = 'none';
        navActions.innerHTML = '';
    };

    // Auth Actions
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('reg-username').value;
        const password = document.getElementById('reg-password').value;

        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
            alert('Cuenta creada. Ahora puedes iniciar sesión.');
            e.target.reset();
        } else {
            alert(data.error || 'Error al registrar');
        }
    });

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
            sessionStorage.setItem('username', data.username);
            showDashboard(data.username);
        } else {
            alert(data.error || 'Error al entrar');
        }
    });

    const logout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        sessionStorage.removeItem('username');
        showAuth();
    };

    // Notes Actions
    const loadNotes = async () => {
        const res = await fetch('/api/notes');
        if (res.status === 401) return showAuth();
        const notes = await res.json();
        
        notesList.innerHTML = notes.map(note => `
            <article class="note-card">
                <h3>${note.title}</h3>
                <small>${new Date(note.created_at).toLocaleString()}</small>
                <p>${note.content}</p>
                <footer>
                    <button class="delete-btn" onclick="deleteNote(${note.id})">Eliminar</button>
                </footer>
            </article>
        `).join('');
    };

    document.getElementById('note-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('note-title').value;
        const content = document.getElementById('note-content').value;

        const res = await fetch('/api/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content })
        });

        if (res.ok) {
            e.target.reset();
            loadNotes();
        } else {
            const data = await res.json();
            alert(data.error || 'Error al guardar nota');
        }
    });

    window.deleteNote = async (id) => {
        if (!confirm('¿Seguro?')) return;
        const res = await fetch(`/api/notes/${id}`, { method: 'DELETE' });
        if (res.ok) loadNotes();
    };

    checkAuth();
});
