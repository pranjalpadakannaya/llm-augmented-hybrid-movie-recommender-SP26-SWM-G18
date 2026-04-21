import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Bell, ChevronDown, User, Layers, LogOut } from 'lucide-react';
import { useScrolled } from '../hooks/useScrolled';

function PopcornIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <path d="M8 14L10 25H18L20 14Z" fill="#E50914" />
      <path d="M10.5 14L11.2 25H12.5L11.8 14Z" fill="rgba(255,255,255,0.28)" />
      <path d="M14.8 14L15.5 25H16.8L16.1 14Z" fill="rgba(255,255,255,0.28)" />
      <rect x="7" y="12" width="14" height="2.5" rx="1.25" fill="#bf0010" />
      <circle cx="11" cy="9.5" r="3" fill="#FFF176" />
      <circle cx="14" cy="7.8" r="3.2" fill="#FFF9C4" />
      <circle cx="17" cy="9.5" r="3" fill="#FFF176" />
      <circle cx="8.5" cy="11.2" r="2" fill="#FFF9C4" />
      <circle cx="19.5" cy="11.2" r="2" fill="#FFF176" />
    </svg>
  );
}

const NAV_LINKS = [
  { label: 'Home', path: '/' },
  { label: 'Discover', path: '/search' },
  { label: 'My Profile', path: '/profile' },
];

export default function Navbar() {
  const scrolled = useScrolled();
  const location = useLocation();
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <motion.nav
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled ? 'glass border-b border-white/5' : 'bg-gradient-to-b from-black/80 to-transparent'
      }`}
    >
      <div className="max-w-screen-2xl mx-auto px-6 md:px-10 h-16 flex items-center gap-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <PopcornIcon size={30} />
          <span className="text-xl font-black tracking-tight text-white">
            Pop<span className="text-[#E50914]">corn</span>
          </span>
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden md:flex items-center gap-6">
          {NAV_LINKS.map((link) => (
            <li key={link.path}>
              <Link
                to={link.path}
                className={`text-sm transition-colors duration-200 ${
                  location.pathname === link.path
                    ? 'text-white font-medium'
                    : 'text-[#aaa] hover:text-white'
                }`}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-4">
          <Link
            to="/search"
            className="p-2 text-[#aaa] hover:text-white transition-colors duration-200 rounded-full hover:bg-white/10"
          >
            <Search size={20} />
          </Link>

          <button className="relative p-2 text-[#aaa] hover:text-white transition-colors duration-200 rounded-full hover:bg-white/10">
            <Bell size={20} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#E50914] rounded-full" />
          </button>

          {/* Profile dropdown */}
          <div className="relative">
            <button
              onClick={() => setProfileOpen((p) => !p)}
              className="flex items-center gap-2 group"
            >
              <div className="w-8 h-8 rounded-md bg-[#E50914] flex items-center justify-center text-white text-xs font-bold">
                PP
              </div>
              <ChevronDown
                size={14}
                className={`text-[#aaa] transition-transform duration-200 ${profileOpen ? 'rotate-180' : ''}`}
              />
            </button>

            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-12 w-52 glass-card rounded-xl border border-white/10 shadow-2xl overflow-hidden"
                >
                  <div className="px-4 py-3 border-b border-white/10">
                    <p className="text-sm font-medium text-white">Pranjal P.</p>
                    <p className="text-xs text-[#aaa] mt-0.5">ppadakan@asu.edu</p>
                  </div>
                  <ul className="py-2">
                    <li>
                      <Link
                        to="/profile"
                        onClick={() => setProfileOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#ccc] hover:text-white hover:bg-white/5 transition-colors"
                      >
                        <User size={15} />
                        My Profile
                      </Link>
                    </li>
                    <li>
                      <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#ccc] hover:text-white hover:bg-white/5 transition-colors">
                        <Layers size={15} />
                        Model Insights
                      </button>
                    </li>
                    <li className="border-t border-white/10 mt-2 pt-2">
                      <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#ccc] hover:text-white hover:bg-white/5 transition-colors">
                        <LogOut size={15} />
                        Sign Out
                      </button>
                    </li>
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-2 text-[#aaa] hover:text-white"
            onClick={() => setMobileOpen((m) => !m)}
          >
            <div className="w-5 flex flex-col gap-1.5">
              <span className={`block h-0.5 bg-current transition-all ${mobileOpen ? 'rotate-45 translate-y-2' : ''}`} />
              <span className={`block h-0.5 bg-current transition-all ${mobileOpen ? 'opacity-0' : ''}`} />
              <span className={`block h-0.5 bg-current transition-all ${mobileOpen ? '-rotate-45 -translate-y-2' : ''}`} />
            </div>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden glass border-t border-white/10"
          >
            <ul className="px-6 py-4 flex flex-col gap-1">
              {NAV_LINKS.map((link) => (
                <li key={link.path}>
                  <Link
                    to={link.path}
                    onClick={() => setMobileOpen(false)}
                    className={`block py-2.5 text-sm transition-colors ${
                      location.pathname === link.path ? 'text-white font-medium' : 'text-[#aaa]'
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
