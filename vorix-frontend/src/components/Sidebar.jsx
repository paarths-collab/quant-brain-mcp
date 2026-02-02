import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  CreditCard, 
  Wallet,
  ArrowLeftRight,
  TrendingUp,
  TestTube,
  Search as SearchIcon,
  Settings,
  Users,
  ChevronRight,
  Receipt,
  Network,
  Globe
} from 'lucide-react';
import './Sidebar.css';

const mainMenuItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/payment', icon: Wallet, label: 'Payment' },
  { path: '/technical', icon: TrendingUp, label: 'Technical' },
  { path: '/backtest', icon: TestTube, label: 'Backtest' },
  { path: '/research', icon: SearchIcon, label: 'Research' },
  { path: '/network', icon: Network, label: 'Network' },
  { path: '/globe', icon: Globe, label: 'Globe' },
];

const otherItems = [
  { path: '/settings', icon: Settings, label: 'Settings' },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <span>V</span>
          <ChevronRight size={12} className="logo-arrow" />
        </div>
        <span className="logo-text">Vorix</span>
      </div>

      <div className="sidebar-search">
        <SearchIcon size={16} />
        <span>Search</span>
        <span className="search-shortcut">Ctrl+K</span>
      </div>

      <div className="sidebar-section">
        <span className="section-label">Main Menu</span>
        <nav className="sidebar-nav">
          {mainMenuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        {otherItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </aside>
  );
}

export default Sidebar;
