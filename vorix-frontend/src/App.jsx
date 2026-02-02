import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Starter from './pages/Starter';
import Dashboard from './pages/Dashboard';
import Payment from './pages/Payment';
import Technical from './pages/Technical';
import Backtest from './pages/Backtest';
import Research from './pages/Research';
import Settings from './pages/Settings';
import Network from './pages/Network';
import Globe from './pages/Globe';
import './index.css';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Starter />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/payment" element={<Payment />} />
            <Route path="/technical" element={<Technical />} />
            <Route path="/backtest" element={<Backtest />} />
            <Route path="/research" element={<Research />} />
            <Route path="/network" element={<Network />} />
            <Route path="/globe" element={<Globe />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
