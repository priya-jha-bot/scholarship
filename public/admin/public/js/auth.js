function requireRole(role) {
  const user = JSON.parse(sessionStorage.getItem("user") || "null");
  if (!user || user.role !== role) {
    location.href = "/login.html";
  }
  return user;
}

async function login(email, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });

  sessionStorage.setItem("token", data.token);
  sessionStorage.setItem("user", JSON.stringify(data.user));

  // Redirect by role
  const rolePaths = {
    student: "/student/dashboard.html",
    admin: "/admin/dashboard.html",
    reviewer: "/reviewer/dashboard.html"
  };
  location.href = rolePaths[data.user.role] || "/index.html";
}

function logout() {
  sessionStorage.clear();
  location.href = "/login.html";
}