import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, LineChart, PieChart, TestTube, 
  Search, Globe, Settings, TrendingUp, MessageCircle,
  Network, Sparkles
} from 'lucide-react';
import './Sidebar.css';

const menuItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/technical', icon: LineChart, label: 'Technical' },
  { path: '/sectors', icon: PieChart, label: 'Sectors' },
  { path: '/backtest', icon: TestTube, label: 'Backtest' },
  { path: '/research', icon: Search, label: 'Research' },
  { path: '/globe', icon: Globe, label: 'Global' },
  { path: '/reddit', icon: MessageCircle, label: 'Reddit' },
  { path: '/relationships', icon: Network, label: 'Relationships' },
  { path: '/ai', icon: Sparkles, label: 'AI Advisor', highlight: true },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <TrendingUp size={24} />
          <span>Bloomberg</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''} ${item.highlight ? 'highlight' : ''}`}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
            {item.highlight && <span className="ai-badge">NEW</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Settings size={18} />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}

export default Sidebar;
