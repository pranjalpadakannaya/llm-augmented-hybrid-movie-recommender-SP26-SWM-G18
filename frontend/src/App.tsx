import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Search from './pages/Search';
import MovieDetail from './pages/MovieDetail';
import Profile from './pages/Profile';
import { fetchUsers } from './api/client';
import { UserOption } from './types';

function AnimatedRoutes({ userId }: { userId: number }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Home userId={userId} />} />
        <Route path="/search" element={<Search userId={userId} />} />
        <Route path="/movie/:id" element={<MovieDetail userId={userId} />} />
        <Route path="/profile" element={<Profile userId={userId} />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  const [users, setUsers] = useState<UserOption[]>([]);
  const [selectedUserId, setSelectedUserId] = useState(1);
  const [usersLoading, setUsersLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let pollId: ReturnType<typeof setInterval> | null = null;

    async function loadUsers() {
      try {
        const data = await fetchUsers();
        if (cancelled) return false;
        if (data.length > 0) {
          setUsers(data);
          setSelectedUserId((current) =>
            data.some((user) => user.userId === current) ? current : data[0].userId
          );
          setUsersLoading(false);
          return true;
        }
      } catch {
        // keep polling until backend becomes ready
      }
      if (!cancelled) {
        setUsers([]);
      }
      return false;
    }

    async function initUsers() {
      const loaded = await loadUsers();
      if (loaded || cancelled) return;

      pollId = setInterval(async () => {
        const ok = await loadUsers();
        if (ok && pollId) {
          clearInterval(pollId);
          pollId = null;
        }
      }, 4000);
    }

    initUsers();

    return () => {
      cancelled = true;
      if (pollId) clearInterval(pollId);
    };
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col">
        <Navbar
          users={users}
          usersLoading={usersLoading}
          selectedUserId={selectedUserId}
          onSelectUser={setSelectedUserId}
        />
        <main className="flex-1">
          <AnimatedRoutes userId={selectedUserId} />
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
