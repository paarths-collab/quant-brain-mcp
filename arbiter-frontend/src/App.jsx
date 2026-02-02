import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Technical from './pages/Technical';
import Sectors from './pages/Sectors';
import Backtest from './pages/Backtest';
import Research from './pages/Research';
import Globe from './pages/Globe';
import Reddit from './pages/Reddit';
import Relationships from './pages/Relationships';
import InvestmentAI from './pages/InvestmentAI';
import Settings from './pages/Settings';
import './index.css';

import { ThemeProvider } from './context/ThemeContext';

const queryClient = new QueryClient();

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/technical" element={<Technical />} />
              <Route path="/sectors" element={<Sectors />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/research" element={<Research />} />
              <Route path="/globe" element={<Globe />} />
              <Route path="/reddit" element={<Reddit />} />
              <Route path="/relationships" element={<Relationships />} />
              <Route path="/ai" element={<InvestmentAI />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
