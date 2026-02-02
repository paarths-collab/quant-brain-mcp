import { Outlet } from 'react-router-dom';
import { Moon, Settings } from 'lucide-react';
import Sidebar from './Sidebar';
import './Layout.css';

function Layout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-area">
        <header className="top-header">
          <div className="header-spacer"></div>
          <div className="header-actions">
            <button className="header-btn"><Moon size={18} /></button>
            <button className="header-btn"><Settings size={18} /></button>
          </div>
        </header>
        <div className="page-container fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default Layout;
