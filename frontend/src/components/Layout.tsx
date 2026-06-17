import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useContentProtection } from '../hooks/useContentProtection';

export default function Layout() {
  useContentProtection();

  return (
    <div className="flex h-screen bg-[#07100c] text-[#dff5ea] overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
