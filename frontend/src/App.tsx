import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Search from './pages/Search';
import MovieDetail from './pages/MovieDetail';
import Profile from './pages/Profile';
import { fetchProfile } from './api/client';
import { UserOption } from './types';

const DEMO_USERS: UserOption[] = [
  {
    userId: 41635,
    displayName: 'User 41635',
    initials: 'U4',
    avatarColor: '#8B5CF6',
    historySummary: 'Leans toward action, adventure, and sci-fi with some 80s comedy.',
    favoriteGenres: [],
  },
  {
    userId: 10311,
    displayName: 'User 10311',
    initials: 'U1',
    avatarColor: '#A855F7',
    historySummary: 'Leans toward comedy, animation, and family-friendly titles.',
    favoriteGenres: [],
  },
  {
    userId: 15769,
    displayName: 'User 15769',
    initials: 'U1',
    avatarColor: '#F59E0B',
    historySummary: 'Leans toward drama, romance, and psychologically heavier films.',
    favoriteGenres: [],
  },
];

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
  const [users, setUsers] = useState<UserOption[]>(DEMO_USERS);
  const [selectedUserId, setSelectedUserId] = useState(DEMO_USERS[0].userId);
  const [usersLoading, setUsersLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setUsers(DEMO_USERS);
    setUsersLoading(true);

    Promise.allSettled(
      DEMO_USERS.map(async (user) => {
        const profile = await fetchProfile(user.userId);
        return {
          userId: profile.userId,
          displayName: profile.displayName,
          initials: profile.initials,
          avatarColor: profile.avatarColor,
          historySummary: profile.historySummary || user.historySummary,
          favoriteGenres: profile.favoriteGenres,
        } satisfies UserOption;
      })
    ).then((results) => {
      if (cancelled) return;
      setUsers(
        results.map((result, index) =>
          result.status === 'fulfilled' ? result.value : DEMO_USERS[index]
        )
      );
      setUsersLoading(false);
    });

    return () => {
      cancelled = true;
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
