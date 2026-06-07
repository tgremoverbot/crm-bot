import { createHashRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Campaigns from './pages/Campaigns';
import CampaignForm from './pages/CampaignForm';
import Materials from './pages/Materials';
import MaterialForm from './pages/MaterialForm';
import Sequences from './pages/Sequences';
import SequenceForm from './pages/SequenceForm';
import Broadcasts from './pages/Broadcasts';
import BroadcastCreate from './pages/BroadcastCreate';
import BroadcastEdit from './pages/BroadcastEdit';

function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <Outlet />;
}

const router = createHashRouter([
  { path: '/login', element: <Login /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: '/', element: <Navigate to="/dashboard" replace /> },
          { path: '/dashboard', element: <Dashboard /> },
          { path: '/users', element: <Users /> },
          { path: '/campaigns', element: <Campaigns /> },
          { path: '/campaigns/new', element: <CampaignForm /> },
          { path: '/campaigns/:id/edit', element: <CampaignForm /> },
          { path: '/materials', element: <Materials /> },
          { path: '/materials/new', element: <MaterialForm /> },
          { path: '/materials/:id/edit', element: <MaterialForm /> },
          { path: '/sequences', element: <Sequences /> },
          { path: '/sequences/new', element: <SequenceForm /> },
          { path: '/sequences/:id/edit', element: <SequenceForm /> },
          { path: '/broadcasts', element: <Broadcasts /> },
          { path: '/broadcasts/new', element: <BroadcastCreate /> },
          { path: '/broadcasts/:id/edit', element: <BroadcastEdit /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
