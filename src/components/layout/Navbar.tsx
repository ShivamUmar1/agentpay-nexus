import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Bot, 
  Layers, 
  PlusCircle, 
  CreditCard, 
  Sliders, 
  Activity, 
  User, 
  LogOut, 
  ExternalLink,
  ChevronDown,
  Sparkles,
  Menu,
  X
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, logout, loginAsGuest } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  // Close menus on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileMenuOpen(false);
        setMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 bg-navy-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-violet-600 p-[1px] shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition-all duration-300">
              <div className="w-full h-full bg-navy-900 rounded-xl flex items-center justify-center">
                <Bot className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-lg tracking-tight text-white">AgentPay</span>
                <span className="text-xs px-1.5 py-0.5 rounded font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">NEXUS</span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono tracking-wider">AUTONOMOUS COMMERCE</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            <Link
              to="/marketplace"
              className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-1.5 ${
                isActive('/marketplace') 
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              Marketplace
            </Link>

            <Link
              to="/dashboard"
              className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-1.5 ${
                isActive('/dashboard') 
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-4 h-4" />
              Dashboard
            </Link>

            <Link
              to="/tasks"
              className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-1.5 ${
                isActive('/tasks') 
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Workflows
            </Link>

            <Link
              to="/settings"
              className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-1.5 ${
                isActive('/settings') 
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Sliders className="w-4 h-4" />
              Diagnostics
            </Link>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            {/* PayPal Sandbox Status Badge */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-blue-950/60 border border-blue-500/30 text-blue-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>PayPal Sandbox</span>
            </div>

            {/* Launch Task CTA */}
            <Link
              to="/create"
              className="px-3.5 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-sm flex items-center gap-1.5 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all duration-200"
            >
              <PlusCircle className="w-4 h-4 stroke-[2.5]" />
              <span className="hidden sm:inline">Dispatch Task</span>
            </Link>

            {/* User Dropdown */}
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-2 p-1 pl-2 rounded-full hover:bg-slate-800/60 border border-slate-700/60 transition-colors"
                >
                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="w-7 h-7 rounded-full object-cover ring-1 ring-cyan-500/40"
                  />
                  <span className="text-xs font-medium text-slate-200 hidden sm:inline">{user.name.split(' ')[0]}</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-xl bg-navy-900 border border-slate-800 shadow-2xl p-1.5 z-50">
                    <div className="px-3 py-2 border-b border-slate-800">
                      <p className="text-xs font-semibold text-white">{user.name}</p>
                      <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                      <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                        {user.role}
                      </span>
                    </div>

                    <Link
                      to="/dashboard"
                      onClick={() => setMenuOpen(false)}
                      className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-lg flex items-center gap-2 mt-1"
                    >
                      <Activity className="w-3.5 h-3.5 text-cyan-400" />
                      Dashboard
                    </Link>

                    <Link
                      to="/settings"
                      onClick={() => setMenuOpen(false)}
                      className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-lg flex items-center gap-2"
                    >
                      <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                      Platform Settings
                    </Link>

                    <button
                      onClick={() => {
                        setMenuOpen(false);
                        logout();
                      }}
                      className="w-full text-left px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10 rounded-lg flex items-center gap-2"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={loginAsGuest}
                className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 hover:border-cyan-500/50 text-slate-200 hover:text-cyan-400 transition-colors"
              >
                Sign In
              </button>
            )}
            {/* Mobile Hamburger Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-xl bg-navy-900 border border-slate-800 text-slate-300 hover:text-white hover:border-cyan-500/40 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 transition-colors"
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-nav-drawer"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-cyan-400" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <nav
          id="mobile-nav-drawer"
          aria-label="Mobile Navigation"
          className="md:hidden border-t border-slate-800/90 bg-navy-950/95 backdrop-blur-xl px-4 py-3 space-y-1 animate-fadeIn shadow-2xl"
        >
          <Link
            to="/marketplace"
            onClick={() => setMobileMenuOpen(false)}
            className={`w-full px-3 py-2.5 rounded-xl transition-colors flex items-center gap-2.5 text-xs font-semibold ${
              isActive('/marketplace')
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Marketplace</span>
          </Link>

          <Link
            to="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className={`w-full px-3 py-2.5 rounded-xl transition-colors flex items-center gap-2.5 text-xs font-semibold ${
              isActive('/dashboard')
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>Dashboard</span>
          </Link>

          <Link
            to="/tasks"
            onClick={() => setMobileMenuOpen(false)}
            className={`w-full px-3 py-2.5 rounded-xl transition-colors flex items-center gap-2.5 text-xs font-semibold ${
              isActive('/tasks')
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>Workflows</span>
          </Link>

          <Link
            to="/settings"
            onClick={() => setMobileMenuOpen(false)}
            className={`w-full px-3 py-2.5 rounded-xl transition-colors flex items-center gap-2.5 text-xs font-semibold ${
              isActive('/settings')
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>Diagnostics</span>
          </Link>

          <div className="pt-2 mt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
            <span className="flex items-center gap-1 text-blue-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              PayPal Sandbox Ready
            </span>
            <span className="text-slate-500">v1.0.0</span>
          </div>
        </nav>
      )}
    </header>
  );
};
