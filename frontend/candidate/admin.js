const API_URL = 'http://localhost:8000';

const loginForm = document.getElementById("login-form");
const emailInput = document.getElementById("email-input");
const passwordInput = document.getElementById("password-input");
const statusPanel = document.getElementById("status-panel");
const authPanel = document.getElementById("auth-panel");
const adminPanel = document.getElementById("admin-panel");
const adminUser = document.getElementById("admin-user");
const logoutButton = document.getElementById("logout-button");

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
    authPanel.classList.add("hidden");
    adminPanel.classList.remove("hidden");
    logoutButton.disabled = false;
    adminUser.textContent = `${user.email} (roles: ${user.roles.join(", ")})`;
    setStatus("You are signed in.", "success");
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

checkSession();
