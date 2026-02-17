const API_URL = 'http://localhost:8000';

// DOM Elements - Auth
const loginForm = document.getElementById("login-form");
const emailInput = document.getElementById("email-input");
const passwordInput = document.getElementById("password-input");
const statusPanel = document.getElementById("status-panel");
const authPanel = document.getElementById("auth-panel");
const adminPanel = document.getElementById("admin-panel");
const adminUser = document.getElementById("admin-user");
const logoutButton = document.getElementById("logout-button");

// DOM Elements - User Management
const createUserButton = document.getElementById("create-user-button");
const usersTableBody = document.getElementById("users-table-body");
const userSearch = document.getElementById("user-search");
const roleFilter = document.getElementById("role-filter");
const statusFilter = document.getElementById("status-filter");

// DOM Elements - Modals
const createUserModal = document.getElementById("create-user-modal");
const editUserModal = document.getElementById("edit-user-modal");
const passwordModal = document.getElementById("password-modal");
const deleteUserModal = document.getElementById("delete-user-modal");

// State
let allUsers = [];
let currentUser = null;

function setStatus(message, tone = "info") {
    statusPanel.textContent = message;
    statusPanel.className = `status-panel status-${tone}`;
}

function showLogin(message = "") {
    authPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    logoutButton.disabled = true;
    if (message) {
        setStatus(message, "error");
    } else {
        setStatus("Please sign in with your admin account.", "info");
    }
}

function showAdmin(user) {
    currentUser = user;
    authPanel.classList.add("hidden");
    adminPanel.classList.remove("hidden");
    logoutButton.disabled = false;
    adminUser.textContent = `${user.email} (roles: ${user.roles.join(", ")})`;
    setStatus("You are signed in.", "success");
    loadUsers();
}

async function checkSession() {
    try {
        const response = await fetch(`${API_URL}/admin/me`, { credentials: "include" });
        if (response.ok) {
            const user = await response.json();
            showAdmin(user);
            return;
        }
        if (response.status === 403) {
            showLogin("Access denied. Admin role required.");
            return;
        }
        showLogin();
    } catch (error) {
        showLogin("Unable to reach the server.");
    }
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus("Signing in...", "info");

    try {
        const response = await fetch(`${API_URL}/admin/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                email: emailInput.value.trim(),
                password: passwordInput.value,
            }),
        });

        if (!response.ok) {
            const payload = await response.json();
            throw new Error(payload.detail || "Login failed");
        }

        const payload = await response.json();
        showAdmin(payload.user);
        passwordInput.value = "";
    } catch (error) {
        showLogin(error.message || "Login failed");
    }
});

logoutButton.addEventListener("click", async () => {
    try {
        await fetch(`${API_URL}/admin/logout`, {
            method: "POST",
            credentials: "include",
        });
    } finally {
        showLogin("Signed out.");
    }
});

// ============================================================================
// User Management
// ============================================================================

async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users?limit=1000`, {
            credentials: "include"
        });
        
        if (!response.ok) {
            throw new Error("Failed to load users");
        }
        
        const data = await response.json();
        allUsers = data.users;
        renderUsers();
    } catch (error) {
        usersTableBody.innerHTML = `<tr><td colspan="5" class="error">Error loading users: ${error.message}</td></tr>`;
    }
}

function renderUsers() {
    const searchTerm = userSearch.value.toLowerCase();
    const roleFilterValue = roleFilter.value;
    const statusFilterValue = statusFilter.value;
    
    let filtered = allUsers.filter(user => {
        const matchesSearch = !searchTerm || user.email.toLowerCase().includes(searchTerm);
        const matchesRole = !roleFilterValue || user.roles.includes(roleFilterValue);
        const matchesStatus = !statusFilterValue || 
            (statusFilterValue === 'active' && user.is_active) ||
            (statusFilterValue === 'inactive' && !user.is_active);
        
        return matchesSearch && matchesRole && matchesStatus;
    });
    
    if (filtered.length === 0) {
        usersTableBody.innerHTML = '<tr><td colspan="5" class="empty">No users found</td></tr>';
        return;
    }
    
    usersTableBody.innerHTML = filtered.map(user => `
        <tr>
            <td>${escapeHtml(user.email)}</td>
            <td><span class="badge-group">${user.roles.map(r => `<span class="badge">${r}</span>`).join('')}</span></td>
            <td><span class="status-badge ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td class="actions">
                <button class="btn-icon" onclick="openEditUserModal(${user.id})" title="Edit user">✎</button>
                <button class="btn-icon" onclick="openPasswordModal(${user.id})" title="Change password">🔑</button>
                <button class="btn-icon delete" onclick="openDeleteUserModal(${user.id})" title="Delete user">🗑</button>
            </td>
        </tr>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Search and filter handlers
userSearch.addEventListener('input', renderUsers);
roleFilter.addEventListener('change', renderUsers);
statusFilter.addEventListener('change', renderUsers);

// ============================================================================
// Create User Modal
// ============================================================================

createUserButton.addEventListener('click', () => {
    openModal(createUserModal);
    document.getElementById('create-user-form').reset();
});

document.getElementById('create-user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('create-email').value.trim();
    const password = document.getElementById('create-password').value;
    const roles = Array.from(document.querySelectorAll('input[name="create-role"]:checked'))
        .map(cb => cb.value);
    
    if (roles.length === 0) {
        setStatus("Please select at least one role", "error");
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password, roles })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create user');
        }
        
        setStatus("User created successfully", "success");
        closeModal(createUserModal);
        await loadUsers();
    } catch (error) {
        setStatus(error.message, "error");
    }
});

// ============================================================================
// Edit User Modal
// ============================================================================

window.openEditUserModal = (userId) => {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-email').value = user.email;
    document.getElementById('edit-is-active').value = user.is_active.toString();
    
    document.querySelectorAll('input[name="edit-role"]').forEach(cb => {
        cb.checked = user.roles.includes(cb.value);
    });
    
    openModal(editUserModal);
};

document.getElementById('edit-user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('edit-user-id').value;
    const email = document.getElementById('edit-email').value.trim();
    const isActive = document.getElementById('edit-is-active').value === 'true';
    const roles = Array.from(document.querySelectorAll('input[name="edit-role"]:checked'))
        .map(cb => cb.value);
    
    if (roles.length === 0) {
        setStatus("Please select at least one role", "error");
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, roles, is_active: isActive })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update user');
        }
        
        setStatus("User updated successfully", "success");
        closeModal(editUserModal);
        await loadUsers();
    } catch (error) {
        setStatus(error.message, "error");
    }
});

// ============================================================================
// Change Password Modal
// ============================================================================

window.openPasswordModal = (userId) => {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('password-user-id').value = user.id;
    document.getElementById('password-user-email').textContent = `Change password for: ${user.email}`;
    document.getElementById('password-form').reset();
    
    openModal(passwordModal);
};

document.getElementById('password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('password-user-id').value;
    const newPassword = document.getElementById('new-password').value;
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}/password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ new_password: newPassword })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to change password');
        }
        
        setStatus("Password changed successfully", "success");
        closeModal(passwordModal);
    } catch (error) {
        setStatus(error.message, "error");
    }
});

// ============================================================================
// Delete User Modal
// ============================================================================

window.openDeleteUserModal = (userId) => {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('delete-user-id').value = user.id;
    document.getElementById('delete-user-email').textContent = user.email;
    
    openModal(deleteUserModal);
};

document.getElementById('confirm-delete').addEventListener('click', async () => {
    const userId = document.getElementById('delete-user-id').value;
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete user');
        }
        
        setStatus("User deleted successfully", "success");
        closeModal(deleteUserModal);
        await loadUsers();
    } catch (error) {
        setStatus(error.message, "error");
    }
});

// ============================================================================
// Modal Utilities
// ============================================================================

function openModal(modal) {
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modal on backdrop click
[createUserModal, editUserModal, passwordModal, deleteUserModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal(modal);
        }
    });
});

// Close modal on X button or Cancel button
document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.modal');
        if (modal) closeModal(modal);
    });
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        [createUserModal, editUserModal, passwordModal, deleteUserModal].forEach(modal => {
            if (!modal.classList.contains('hidden')) {
                closeModal(modal);
            }
        });
    }
});

// ============================================================================
// Initialize
// ============================================================================

checkSession();
