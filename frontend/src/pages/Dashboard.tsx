import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api/stats';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { Users, Megaphone, BookOpen, GitBranch, Radio, Send } from 'lucide-react';

const icons = [Users, Megaphone, BookOpen, GitBranch, Radio, Send];
const labels = [
  'Total Users',
  'Campaigns',
  'Materials',
  'Sequences',
  'Broadcasts',
  'Pending Messages',
];

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['stats'],
    queryFn: statsApi.get,
  });

  const values = data
    ? [
        data.users.total,
        data.campaigns.total,
        data.materials.total,
        data.sequences.total,
        data.broadcasts.total,
        data.scheduled.pending,
      ]
    : [];

  return (
    <div className="p-6">
      <PageHeader title="Dashboard" subtitle="Overview of your CRM activity" />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load stats." />}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {labels.map((label, i) => {
            const Icon = icons[i];
            return (
              <div key={label} className="card p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-brand-500/10">
                    <Icon size={16} className="text-brand-400" />
                  </div>
                  <span className="text-xs text-[#4a7060] font-medium uppercase tracking-wider">
                    {label}
                  </span>
                </div>
                <p className="text-3xl font-bold text-[#dff5ea] font-mono">
                  {(values[i] ?? 0).toLocaleString()}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
