import { LayoutDashboard, LineChart, PieChart, FlaskConical, Settings, LogOut } from "lucide-react";
import Link from "next/link";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-screen w-full bg-black text-white">
            {/* Sidebar */}
            <aside className="w-64 flex-shrink-0 glass-panel border-r border-white/10 m-2 rounded-xl flex flex-col">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-xl font-bold tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
                        BOOMERANG
                    </h2>
                    <span className="text-xs text-gray-500">INSTITUTIONAL</span>
                </div>

                <nav className="flex-1 px-4 py-6 space-y-2">
                    <NavItem href="/dashboard" icon={<LayoutDashboard size={18} />} label="Overview" active />
                    <NavItem href="/dashboard/analysis" icon={<LineChart size={18} />} label="Market Analysis" />
                    <NavItem href="/dashboard/portfolio" icon={<PieChart size={18} />} label="Portfolio" />
                    <NavItem href="/dashboard/research" icon={<FlaskConical size={18} />} label="AI Research" />
                </nav>

                <div className="p-4 border-t border-white/10 space-y-2">
                    <NavItem href="/settings" icon={<Settings size={18} />} label="Settings" />
                    <button className="flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-white/5 rounded-lg w-full transition-colors">
                        <LogOut size={18} />
                        <span>Logout</span>
                    </button>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col min-w-0 overflow-hidden m-2 ml-0 rounded-xl glass-panel border border-white/10 relative">
                <div className="absolute inset-0 overflow-y-auto p-6 scroll-smooth">
                    {children}
                </div>
            </main>
        </div>
    );
}

function NavItem({ href, icon, label, active = false }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
    return (
        <Link
            href={href}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200
        ${active
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
        >
            {icon}
            <span>{label}</span>
        </Link>
    );
}
