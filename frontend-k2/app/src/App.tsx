import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Technical from './pages/Technical';
import Sectors from './pages/Sectors';
import Backtest from './pages/Backtest';
import Research from './pages/Research';
import Globe from './pages/Globe';
import Reddit from './pages/Reddit';
import Relationships from './pages/Relationships';
import AIChat from './pages/AIChat';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/technical" element={<Technical />} />
          <Route path="/sectors" element={<Sectors />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/research" element={<Research />} />
          <Route path="/globe" element={<Globe />} />
          <Route path="/reddit" element={<Reddit />} />
          <Route path="/relationships" element={<Relationships />} />
          <Route path="/chat" element={<AIChat />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
