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
    loadCategories();
}

async function checkSession() {
    try {
        const response = await fetch(`${API_URL}/admin/me`, { credentials: "include" });
        if (response.ok) {
            const user = await response.json();
            showAdmin(user);
            return;
        }
        // Handle 401 (Unauthorized) and 403 (Forbidden) - both require login
        if (response.status === 401 || response.status === 403) {
            const message = response.status === 403 ? "Access denied. Admin role required." : null;
            showLogin(message);
            return;
        }
        // Other errors
        showLogin("Unable to verify session.");
    } catch (error) {
        console.error("Error checking session:", error);
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
// Category Management
// ============================================================================

// DOM Elements - Category Management
const createCategoryButton = document.getElementById("create-category-button");
const categoriesTableBody = document.getElementById("categories-table-body");
const categorySearch = document.getElementById("category-search");
const strategyFilter = document.getElementById("strategy-filter");
const uploadForm = document.getElementById("upload-form");

// DOM Elements - Category Modals
const createCategoryModal = document.getElementById("create-category-modal");
const editCategoryModal = document.getElementById("edit-category-modal");
const deleteCategoryModal = document.getElementById("delete-category-modal");

// State
let allCategories = [];

async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/admin/categories`, { credentials: "include" });
        if (!response.ok) throw new Error("Failed to load categories");
        
        allCategories = await response.json();
        renderCategories();
        setStatus("Categories loaded.", "success");
    } catch (error) {
        console.error("Error loading categories:", error);
        setStatus("Failed to load categories", "error");
    }
}

function renderCategories() {
    const searchTerm = categorySearch.value.toLowerCase();
    const strategyValue = strategyFilter.value;
    
    let filtered = allCategories.filter(cat => {
        const matchesSearch = cat.name.toLowerCase().includes(searchTerm);
        const matchesStrategy = !strategyValue || cat.strategy_name === strategyValue;
        return matchesSearch && matchesStrategy;
    });
    
    if (filtered.length === 0) {
        categoriesTableBody.innerHTML = '<tr><td colspan="5" class="empty">No categories found</td></tr>';
        return;
    }
    
    categoriesTableBody.innerHTML = filtered.map(cat => `
        <tr>
            <td>${escapeHtml(cat.name)}</td>
            <td>${cat.strategy_name ? escapeHtml(cat.strategy_name) : '-'}</td>
            <td>${cat.description ? escapeHtml(cat.description.substring(0, 50)) + '...' : '-'}</td>
            <td>${new Date(cat.created_at).toLocaleDateString()}</td>
            <td class="actions">
                <button class="btn-small edit-category" data-id="${cat.id}">Edit</button>
                <button class="btn-small delete-category" data-id="${cat.id}">Delete</button>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners
    document.querySelectorAll('.edit-category').forEach(btn => {
        btn.addEventListener('click', () => openEditCategoryModal(parseInt(btn.dataset.id)));
    });
    document.querySelectorAll('.delete-category').forEach(btn => {
        btn.addEventListener('click', () => openDeleteCategoryModal(parseInt(btn.dataset.id)));
    });
}

function openModal(modal) {
    modal.classList.remove('hidden');
}

function closeModal(modal) {
    modal.classList.add('hidden');
}

function openCreateCategoryModal() {
    document.getElementById('create-category-form').reset();
    openModal(createCategoryModal);
}

function openEditCategoryModal(categoryId) {
    const category = allCategories.find(c => c.id === categoryId);
    if (!category) return;
    
    document.getElementById('edit-category-id').value = categoryId;
    document.getElementById('edit-category-name').value = category.name;
    document.getElementById('edit-category-description').value = category.description || '';
    document.getElementById('edit-category-strategy').value = category.strategy_name || '';
    
    openModal(editCategoryModal);
}

function openDeleteCategoryModal(categoryId) {
    const category = allCategories.find(c => c.id === categoryId);
    if (!category) return;
    
    document.getElementById('delete-category-id').value = categoryId;
    document.getElementById('delete-category-name').textContent = category.name;
    
    openModal(deleteCategoryModal);
}

// Category Event Listeners
createCategoryButton.addEventListener('click', openCreateCategoryModal);

document.getElementById('create-category-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('create-category-name').value.trim();
    const description = document.getElementById('create-category-description').value.trim();
    const strategy_name = document.getElementById('create-category-strategy').value || null;
    
    if (!name) {
        setStatus("Category name is required", "error");
        return;
    }
    
    try {
        setStatus("Creating category...", "info");
        const response = await fetch(`${API_URL}/admin/categories`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description: description || null,
                strategy_name
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to create category");
        }
        
        await loadCategories();
        closeModal(createCategoryModal);
        setStatus("Category created successfully", "success");
    } catch (error) {
        console.error("Error creating category:", error);
        setStatus(error.message || "Failed to create category", "error");
    }
});

document.getElementById('edit-category-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const categoryId = document.getElementById('edit-category-id').value;
    const name = document.getElementById('edit-category-name').value.trim();
    const description = document.getElementById('edit-category-description').value.trim();
    const strategy_name = document.getElementById('edit-category-strategy').value || null;
    
    if (!name) {
        setStatus("Category name is required", "error");
        return;
    }
    
    try {
        setStatus("Updating category...", "info");
        const response = await fetch(`${API_URL}/admin/categories/${categoryId}`, {
            method: 'PATCH',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description: description || null,
                strategy_name
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to update category");
        }
        
        await loadCategories();
        closeModal(editCategoryModal);
        setStatus("Category updated successfully", "success");
    } catch (error) {
        console.error("Error updating category:", error);
        setStatus(error.message || "Failed to update category", "error");
    }
});

document.getElementById('confirm-delete-category').addEventListener('click', async () => {
    const categoryId = document.getElementById('delete-category-id').value;
    
    try {
        setStatus("Deleting category...", "info");
        const response = await fetch(`${API_URL}/admin/categories/${categoryId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to delete category");
        }
        
        await loadCategories();
        closeModal(deleteCategoryModal);
        setStatus("Category deleted successfully", "success");
    } catch (error) {
        console.error("Error deleting category:", error);
        setStatus(error.message || "Failed to delete category", "error");
    }
});

// Upload Event Listeners
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const categoryName = document.getElementById('upload-category-name').value.trim();
    const fileInput = document.getElementById('upload-json-file');
    const textareaData = document.getElementById('upload-json-data').value.trim();
    const overwrite = document.getElementById('upload-overwrite').checked;
    
    if (!categoryName) {
        setStatus("Category name is required", "error");
        return;
    }
    
    let jsonData = textareaData;
    
    // If file is selected, read it
    if (fileInput.files.length > 0) {
        try {
            jsonData = await readFileAsText(fileInput.files[0]);
        } catch (error) {
            setStatus("Error reading file: " + error.message, "error");
            return;
        }
    }
    
    if (!jsonData) {
        setStatus("Please select a JSON file or paste JSON data", "error");
        return;
    }
    
    let parsedJson;
    try {
        parsedJson = JSON.parse(jsonData);
    } catch (error) {
        setStatus("Invalid JSON format: " + error.message, "error");
        return;
    }
    
    try {
        setStatus("Uploading data...", "info");
        const response = await fetch(`${API_URL}/admin/uploads`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category_name: categoryName,
                json_data: parsedJson,
                overwrite
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to upload data");
        }
        
        const result = await response.json();
        await loadCategories();
        uploadForm.reset();
        setStatus(`Upload successful! Added ${result.events_inserted} events.`, "success");
    } catch (error) {
        console.error("Error uploading data:", error);
        setStatus(error.message || "Failed to upload data", "error");
    }
});

// File reading helper
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error("Failed to read file"));
        reader.readAsText(file);
    });
}

// Search and filter handlers
categorySearch.addEventListener('input', renderCategories);
strategyFilter.addEventListener('change', renderCategories);

// ============================================================================
// Modal Management
// ============================================================================

checkSession();
