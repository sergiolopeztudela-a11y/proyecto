document.addEventListener('DOMContentLoaded', () => {
    const authSection = document.getElementById('auth-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const notesList = document.getElementById('notes-list');
    const navActions = document.getElementById('nav-actions');

    // UI Helpers
    const escapeHTML = (str) => {
        const p = document.createElement('p');
        p.textContent = str;
        return p.innerHTML;
    };

    const showError = (msg) => {
        alert(msg);
    };

    // Toggle Auth Logic
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const authTitle = document.getElementById('auth-title');
    const authSubtitle = document.getElementById('auth-subtitle');
    const toggleText = document.getElementById('toggle-text');

    let isRegisterMode = false;

    const updateAuthUI = () => {
        if (isRegisterMode) {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
            authTitle.textContent = 'Crear Cuenta';
            authSubtitle.textContent = 'Únete para guardar tus notas privadas';
            toggleText.innerHTML = '¿Ya tienes cuenta? <a href="#" id="toggle-auth">Inicia sesión aquí</a>';
        } else {
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
            authTitle.textContent = 'Iniciar Sesión';
            authSubtitle.textContent = 'Bienvenido de nuevo a SecureNotes';
            toggleText.innerHTML = '¿No tienes cuenta? <a href="#" id="toggle-auth">Regístrate aquí</a>';
        }
    };

    const handleToggle = (e) => {
        if (e.target.id !== 'toggle-auth') return;
        e.preventDefault();
        isRegisterMode = !isRegisterMode;
        updateAuthUI();
    };

    // Use event delegation on the parent container
    toggleText.addEventListener('click', handleToggle);

    // Registration Inputs
    const regUser = document.getElementById('reg-username');
    const regPass = document.getElementById('reg-password');
    const reqs = {
        len: document.getElementById('req-len'),
        upper: document.getElementById('req-upper'),
        num: document.getElementById('req-num'),
        spec: document.getElementById('req-spec')
    };

    const updateValidation = () => {
        const val = regPass.value;
        const checks = {
            len: val.length >= 10,
            upper: /[A-Z]/.test(val) && /[a-z]/.test(val),
            num: /[0-9]/.test(val),
            spec: /[@#$¡*]/.test(val)
        };

        // Use classList for CSP compatibility
        Object.keys(checks).forEach(k => {
            if (checks[k]) reqs[k].classList.add('valid');
            else reqs[k].classList.remove('valid');
        });
    };

    regPass.addEventListener('input', updateValidation);

    const showDashboard = (username) => {
        authSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        navActions.innerHTML = `
            <li>Hola, ${escapeHTML(username)}</li>
            <li><a href="#" id="logout-btn" role="button" class="outline">Salir</a></li>
        `;
        document.getElementById('logout-btn').addEventListener('click', logout);
        loadNotes();
    };

    const showAuth = () => {
        authSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
        navActions.innerHTML = '';
        updateAuthUI();
    };

    // Auth Actions
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = regUser.value.trim();
        const password = regPass.value;

        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
            showError('Cuenta creada. Ahora puedes iniciar sesión.');
            isRegisterMode = false; // Force switch to login mode
            updateAuthUI();
            e.target.reset();
            updateValidation();
        } else {
            showError(data.error || 'Error al registrar');
        }
    });

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;

        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
            sessionStorage.setItem('username', data.username);
            showDashboard(data.username);
        } else {
            showError(data.error || 'Error al entrar');
        }
    });

    const logout = async () => {
        await fetch('/api/logout', { 
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        sessionStorage.removeItem('username');
        showAuth();
    };

    const loadNotes = async () => {
        const res = await fetch('/api/notes', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.status === 401) return showAuth();
        const notes = await res.json();
        
        notesList.innerHTML = notes.map(note => `
            <article class="note-card">
                <header>
                    <strong>${escapeHTML(note.title)}</strong>
                    <button class="delete-btn" onclick="deleteNote(${note.id})" style="float: right;">✕</button>
                </header>
                <p>${escapeHTML(note.content)}</p>
                <footer>
                    <small>${new Date(note.created_at).toLocaleString()}</small>
                </footer>
            </article>
        `).join('');
    };

    document.getElementById('note-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('note-title').value.trim();
        const content = document.getElementById('note-content').value.trim();
        const res = await fetch('/api/notes', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ title, content })
        });
        if (res.ok) {
            e.target.reset();
            loadNotes();
        } else {
            const data = await res.json();
            showError(data.error || 'Error al guardar nota');
        }
    });

    window.deleteNote = async (id) => {
        if (!confirm('¿Seguro?')) return;
        const res = await fetch(`/api/notes/${id}`, { 
            method: 'DELETE',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.ok) loadNotes();
    };

    const savedUser = sessionStorage.getItem('username');
    if (savedUser) showDashboard(savedUser);
    else showAuth();
});
