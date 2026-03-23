import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  Globe,
  MessageSquare,
  Layers,
  BarChart3,
  Search,
  Network,
  MessagesSquare,
  User,
  Settings,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { name: 'Technical Analysis', to: '/technical', icon: TrendingUp },
  { name: 'Sectors', to: '/sectors', icon: Layers },
  { name: 'Backtest', to: '/backtest', icon: BarChart3 },
  { name: 'Research', to: '/research', icon: Search },
  { name: 'Global Markets', to: '/globe', icon: Globe },
  { name: 'News Box', to: '/reddit', icon: MessagesSquare },
  { name: 'Peer Comparison', to: '/relationships', icon: Network },
  { name: 'AI Chat', to: '/chat', icon: MessageSquare },
  { name: 'Profile', to: '/profile', icon: User },
  { name: 'Settings', to: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-black border-r border-white/10 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
            <span className="text-black font-display font-bold text-lg">B</span>
          </div>
          <span className="font-display font-bold text-lg text-white">Boomerang</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${isActive
                  ? 'bg-purple/20 text-white border border-purple/50'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <p className="text-white/40 text-xs text-center">
          © 2026 Boomerang
        </p>
      </div>
    </aside>
  );
}
