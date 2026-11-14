import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, HOME_BY_ROLE } from '../AuthContext';
import { api, getToken } from '../api';

const NAV = {
  student: [['/student', 'Dashboard']],
  admin: [['/admin', 'Applications'], ['/admin/scholarships', 'Scholarships'], ['/admin/users', 'Create user'], ['/admin/reports', 'Reports']],
  reviewer: [['/reviewer', 'Reviews']],
};

/* FE-8: live notifications. Tries WebSocket first, falls back to polling every 15 s. */
function useNotifications(user) {
  const [items, setItems] = useState([]);
  const pollTimer = useRef();

  const load = useCallback(() => {
    api.get('/notifications').then((r) => setItems(r.items || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) { setItems([]); return; }
    load();
    let ws;
    const startPolling = () => { clearInterval(pollTimer.current); pollTimer.current = setInterval(load, 15000); };
    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${proto}://${location.host}/ws?token=${getToken()}`);
      ws.onmessage = (e) => { try { setItems((prev) => [JSON.parse(e.data), ...prev]); } catch { load(); } };
      ws.onerror = startPolling;
      ws.onclose = startPolling;
    } catch { startPolling(); }
    return () => { clearInterval(pollTimer.current); ws && ws.close(); };
  }, [user, load]);

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read`).catch(() => {});
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };
  return { items, markRead };
}

function Bell({ user }) {
  const { items, markRead } = useNotifications(user);
  const [open, setOpen] = useState(false);
  const unread = items.filter((n) => !n.read).length;
  return (
    <>
      <button className="bell" onClick={() => setOpen(!open)} aria-label="Notifications">
        🔔{unread > 0 && <span className="count">{unread}</span>}
      </button>
      {open && (
        <div className="notif-panel">
          {items.length === 0 && <div className="item muted">No notifications</div>}
          {items.map((n) => (
            <div key={n.id} className={`item ${n.read ? '' : 'unread'}`} onClick={() => markRead(n.id)}>
              {n.message}
              <div className="muted">{new Date(n.created_at).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <>
      <nav className="navbar">
        <Link to={user ? HOME_BY_ROLE[user.role] : '/'} className="brand">🎓 Scholarship Portal</Link>
        {user && NAV[user.role].map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
        {user ? (
          <>
            <Bell user={user} />
            <span className="muted">{user.full_name} ({user.role})</span>
            <button className="btn secondary" onClick={() => { logout(); navigate('/'); }}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register" className="btn">Register</Link>
          </>
        )}
      </nav>
      <main className="container">{children}</main>
    </>
  );
}
