const API_BASE = "/api"; // Change if your backend uses a different prefix

async function apiFetch(endpoint, options = {}) {
  const token = sessionStorage.getItem("token");
  const headers = { ...(options.headers || {}) };

  // Don't set Content-Type if sending FormData (file uploads)
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

    if (res.status === 429) {
      showToast("Please wait and try again", true);
      throw new Error("429 Too Many Requests");
    }

    if (res.status === 401) {
      sessionStorage.clear();
      location.href = "/login.html";
      return;
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.message || `Error ${res.status}`);
    }
    return data;
  } catch (err) {
    if (err.message !== "429 Too Many Requests") {
      showToast(err.message || "Something went wrong", true);
    }
    throw err;
  }
}