import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
  avatar: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loginAsGuest: () => void;
  login: (email: string, name?: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_USER: User = {
  id: 'user_guest_01',
  email: 'alex.vance@nexus.ai',
  name: 'Alex Vance',
  avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256',
  role: 'AI Systems Architect'
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('agentpay_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // ignore
      }
    }
    return DEMO_USER;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('agentpay_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('agentpay_user');
    }
  }, [user]);

  const loginAsGuest = () => {
    setUser(DEMO_USER);
  };

  const login = (email: string, name?: string) => {
    setUser({
      id: 'user_auth_' + Math.random().toString(36).substring(2, 9),
      email,
      name: name || email.split('@')[0],
      avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=256',
      role: 'Enterprise Member'
    });
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, loginAsGuest, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
