/**
 * Authentication & Session Management Module
 * Cohort Marketing Performance Dashboard
 */

const Auth = {
  TOKEN_KEY: "bambinos_cohort_auth_token",
  USER_KEY: "bambinos_cohort_auth_user",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  getUser() {
    try {
      const u = localStorage.getItem(this.USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch (e) {
      return null;
    }
  },

  setSession(token, user) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    this.updateUserUI(user);
  },

  clearSession() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.updateUserUI(null);
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  updateUserUI(user) {
    const userBadge = document.getElementById("headerUserBadge");
    const userNameSpan = document.getElementById("headerUserName");
    const userRoleSpan = document.getElementById("headerUserRole");
    const loginOverlay = document.getElementById("loginOverlay");

    if (user && this.isAuthenticated()) {
      if (userBadge) userBadge.style.display = "inline-flex";
      if (userNameSpan) userNameSpan.textContent = user.name || user.username;
      if (userRoleSpan) userRoleSpan.textContent = user.role || "Executive";
      if (loginOverlay) {
        loginOverlay.classList.remove("active");
        setTimeout(() => { loginOverlay.style.display = "none"; }, 300);
      }
    } else {
      if (userBadge) userBadge.style.display = "none";
      if (loginOverlay) {
        loginOverlay.style.display = "flex";
        setTimeout(() => { loginOverlay.classList.add("active"); }, 10);
      }
    }
  },

  async login(username, password) {
    const errorEl = document.getElementById("loginError");
    const btnEl = document.getElementById("btnLoginSubmit");
    const btnText = document.getElementById("btnLoginText");
    const btnSpinner = document.getElementById("btnLoginSpinner");

    if (errorEl) errorEl.style.display = "none";
    if (btnEl) btnEl.disabled = true;
    if (btnText) btnText.textContent = "Authenticating...";
    if (btnSpinner) btnSpinner.style.display = "inline-block";

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Invalid credentials. Please verify username and password.");
      }

      this.setSession(data.access_token, data.user);

      // Trigger app initialization if not already loaded
      if (typeof App !== "undefined" && App.init) {
        App.init();
      }

      return true;
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message || "Failed to authenticate.";
        errorEl.style.display = "block";
      }
      return false;
    } finally {
      if (btnEl) btnEl.disabled = false;
      if (btnText) btnText.textContent = "Sign In to Marketing Suite";
      if (btnSpinner) btnSpinner.style.display = "none";
    }
  },

  async logout() {
    try {
      const token = this.getToken();
      if (token) {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          }
        });
      }
    } catch (e) {
      console.warn("Logout API call failed:", e);
    } finally {
      this.clearSession();
    }
  },

  async verifyToken() {
    const token = this.getToken();
    if (!token) {
      this.updateUserUI(null);
      return false;
    }

    try {
      const res = await fetch("/api/v1/auth/me", {
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (res.ok) {
        const user = await res.json();
        this.setSession(token, user);
        return true;
      } else {
        this.clearSession();
        return false;
      }
    } catch (e) {
      // Network/offline error; keep session if present or fallback
      const cachedUser = this.getUser();
      if (cachedUser) {
        this.updateUserUI(cachedUser);
        return true;
      }
      this.clearSession();
      return false;
    }
  }
};

/**
 * Global Authenticated Fetch Wrapper
 * Automatically attaches Authorization header and catches 401 Unauthorized
 */
async function authFetch(url, options = {}) {
  const token = Auth.getToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const updatedOptions = { ...options, headers };

  const response = await fetch(url, updatedOptions);

  if (response.status === 401) {
    console.warn("Session expired or unauthorized. Showing login screen.");
    Auth.clearSession();
    throw new Error("Authentication required. Please log in.");
  }

  return response;
}

// Attach to window for global access across scripts
window.Auth = Auth;
window.authFetch = authFetch;
