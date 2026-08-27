import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getToken, setToken, clearToken, getMe, loginUser, registerUser, AUTH_EXPIRED_EVENT } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadUser = useCallback(async () => {
        if (!getToken()) {
            setUser(null);
            setLoading(false);
            return;
        }
        try {
            const me = await getMe();
            setUser(me);
        } catch (e) {
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadUser();
        const onExpired = () => setUser(null);
        window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
        return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
    }, [loadUser]);

    const login = async (email, password) => {
        await loginUser({ email, password });
        await loadUser();
    };

    const register = async ({ email, password, fullName, role }) => {
        await registerUser({ email, password, fullName, role });
        await login(email, password);
    };

    const logout = () => {
        clearToken();
        setUser(null);
    };

    // Used by the GitHub OAuth callback page: the token was issued by the
    // backend after a redirect round-trip, not by a login() call here.
    const loginWithToken = async (token) => {
        setToken(token);
        await loadUser();
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, loginWithToken, refreshUser: loadUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
    return ctx;
}
