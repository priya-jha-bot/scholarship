import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, getToken, setToken } from './api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export const HOME_BY_ROLE = { student: '/student', admin: '/admin', reviewer: '/reviewer' };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, if a token exists, ask the backend who we are.
  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    api.get('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  // api.js fires this event when a request gets a 401.
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener('auth:expired', onExpired);
    return () => window.removeEventListener('auth:expired', onExpired);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    setToken(res.access_token);
    const me = res.user || (await api.get('/auth/me'));
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (data) => {
    await api.post('/auth/register', data);
    return login(data.email, data.password);
  }, [login]);

  const logout = useCallback(() => { setToken(null); setUser(null); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
