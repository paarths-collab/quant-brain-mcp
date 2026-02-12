import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-black">
      <Sidebar />
      <main className="flex-1 ml-64">
        <div className="min-h-screen p-6 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
