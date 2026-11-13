// Show a pop-up message
function showToast(message, isError = false) {
  let box = document.getElementById("toast-box");
  if (!box) {
    box = document.createElement("div");
    box.id = "toast-box";
    document.body.appendChild(box);
  }
  const el = document.createElement("div");
  el.className = `toast ${isError ? "error" : ""}`;
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// Show or hide a loading message inside any container
function setLoading(container, isLoading, text = "Loading...") {
  if (!container) return;
  if (isLoading) {
    container.innerHTML = `<p style="color: var(--muted); padding: 1rem;">⏳ ${text}</p>`;
  }
}

// Turn status text into a colored pill
function renderBadge(status = "Pending") {
  const clean = status.toLowerCase();
  let cls = "badge-pending";
  if (clean.includes("verif")) cls = "badge-verified";
  else if (clean.includes("approv")) cls = "badge-approved";
  else if (clean.includes("reject") || clean.includes("withdraw")) cls = "badge-rejected";
  return `<span class="badge ${cls}">${status}</span>`;
}

// Reusable pagination buttons (10-20 items per page)
function renderPagination(container, currentPage, totalPages, onPageChange) {
  if (!container) return;
  container.innerHTML = "";
  if (totalPages <= 1) return;

  const prev = document.createElement("button");
  prev.className = "btn btn-secondary";
  prev.textContent = "← Prev";
  prev.disabled = currentPage <= 1;
  prev.onclick = () => onPageChange(currentPage - 1);

  const info = document.createElement("span");
  info.style.margin = "0 0.75rem";
  info.textContent = `Page ${currentPage} of ${totalPages}`;

  const next = document.createElement("button");
  next.className = "btn btn-secondary";
  next.textContent = "Next →";
  next.disabled = currentPage >= totalPages;
  next.onclick = () => onPageChange(currentPage + 1);

  container.append(prev, info, next);
}

// Wait 300ms after user stops typing before searching
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}