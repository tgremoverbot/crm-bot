import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api/stats';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import type { Stats } from '../types';

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function dayLabel(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00Z`);
  return DAY_LABELS[d.getUTCDay()] ?? dateStr;
}

interface KpiCardProps {
  label: string;
  value: number;
  trend: 'up' | 'flat';
}

function KpiCard({ label, value, trend }: KpiCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <p className="text-3xl font-bold text-[#dff5ea] font-mono">
          {value.toLocaleString()}
        </p>
        <span className="text-brand-400 text-lg" aria-hidden="true">
          {trend === 'up' ? '↑' : '→'}
        </span>
      </div>
      <span className="mt-2 block text-xs text-[#4a7060] font-medium uppercase tracking-wider">
        {label}
      </span>
    </div>
  );
}

function GrowthChart({ days }: { days: Stats['growth']['last_7_days'] }) {
  const max = Math.max(1, ...days.map((d) => d.new_users));
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#dff5ea] mb-4">
        New subscribers — last 7 days
      </h3>
      {days.length === 0 ? (
        <p className="text-sm text-[#4a7060]">No data yet</p>
      ) : (
        <div className="flex items-end justify-between gap-2 h-44">
          {days.map((d) => {
            const heightPct = (d.new_users / max) * 100;
            return (
              <div
                key={d.date}
                className="flex flex-1 flex-col items-center justify-end h-full"
              >
                <span className="text-xs font-mono text-[#dff5ea] mb-1">
                  {d.new_users}
                </span>
                <div
                  className="w-full rounded-t bg-brand-500"
                  style={{ height: `${Math.max(heightPct, 2)}%` }}
                  title={`${d.date}: ${d.new_users}`}
                />
                <span className="mt-2 text-[10px] text-[#4a7060] uppercase tracking-wide">
                  {dayLabel(d.date)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DeliveryPanel({
  rate,
  pending,
}: {
  rate: number | null;
  pending: number;
}) {
  let color = '#6b7280'; // gray
  let label = 'No data';
  if (rate !== null) {
    const pct = rate * 100;
    if (pct >= 90) {
      color = '#34d399';
      label = 'Healthy';
    } else if (pct >= 70) {
      color = '#fbbf24';
      label = 'Review needed';
    } else {
      color = '#f87171';
      label = 'Action required';
    }
  }
  const display = rate !== null ? `${(rate * 100).toFixed(1)}%` : 'N/A';

  return (
    <div className="card p-5 flex flex-col">
      <h3 className="text-sm font-semibold text-[#dff5ea] mb-4">
        Auto-flow delivery
      </h3>
      <div className="flex flex-col items-center justify-center flex-1">
        <p className="text-5xl font-bold font-mono" style={{ color }}>
          {display}
        </p>
        <span
          className="mt-2 text-sm font-medium"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <p className="mt-4 text-xs text-[#4a7060]">
        Pending messages:{' '}
        <span className="text-[#dff5ea] font-mono">
          {pending.toLocaleString()}
        </span>
      </p>
    </div>
  );
}

function InviteLinksTable({
  links,
}: {
  links: Stats['funnels']['invite_links'];
}) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#dff5ea] mb-4">
        Invite links performance
      </h3>
      {links.length === 0 ? (
        <p className="text-sm text-[#4a7060]">No invite links yet</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] text-[#4a7060] uppercase tracking-wider">
                <th className="pb-2 font-medium">Link keyword</th>
                <th className="pb-2 font-medium text-right">Joined</th>
                <th className="pb-2 font-medium text-right">Seq. delivered</th>
                <th className="pb-2 font-medium text-right">Delivery rate</th>
              </tr>
            </thead>
            <tbody>
              {links.slice(0, 10).map((link) => {
                const rate =
                  link.joined === 0
                    ? '—'
                    : `${((link.sequence_delivered / link.joined) * 100).toFixed(0)}%`;
                return (
                  <tr
                    key={link.slug}
                    className="border-t border-white/5 text-[#dff5ea]"
                  >
                    <td className="py-2 font-mono text-brand-300">
                      {link.slug}
                    </td>
                    <td className="py-2 text-right font-mono">{link.joined}</td>
                    <td className="py-2 text-right font-mono">
                      {link.sequence_delivered}
                    </td>
                    <td className="py-2 text-right font-mono">{rate}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  sent: '#34d399',
  sending: '#60a5fa',
  scheduled: '#fbbf24',
  failed: '#f87171',
  cancelled: '#9ca3af',
  draft: '#9ca3af',
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status.toLowerCase()] ?? '#9ca3af';
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
      style={{ color, backgroundColor: `${color}22` }}
    >
      {status}
    </span>
  );
}

function RecentSends({
  broadcasts,
}: {
  broadcasts: Stats['broadcasts']['recent'];
}) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#dff5ea] mb-4">Recent sends</h3>
      {broadcasts.length === 0 ? (
        <p className="text-sm text-[#4a7060]">No broadcasts yet</p>
      ) : (
        <ul className="space-y-4">
          {broadcasts.map((b) => {
            const pct =
              b.recipient_count > 0
                ? (b.success_count / b.recipient_count) * 100
                : 0;
            return (
              <li key={b.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#dff5ea] truncate pr-2">
                    {b.name}
                  </span>
                  <StatusBadge status={b.status} />
                </div>
                <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="mt-1 text-[10px] text-[#4a7060] font-mono">
                  {b.success_count} / {b.recipient_count} sent
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['stats'],
    queryFn: statsApi.get,
  });

  const newThisWeek = data
    ? data.growth.last_7_days.reduce((sum, d) => sum + d.new_users, 0)
    : 0;
  const messagesDelivered = data
    ? data.broadcasts.recent.reduce((sum, b) => sum + b.success_count, 0) ||
      data.broadcasts.sent
    : 0;

  return (
    <div className="p-6">
      <PageHeader title="Dashboard" subtitle="Overview of your CRM activity" />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load stats." />}

      {data && (
        <div className="space-y-6">
          {/* Zone 1 — Hero KPI row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Total subscribers"
              value={data.users.total}
              trend="up"
            />
            <KpiCard
              label="New this week"
              value={newThisWeek}
              trend={newThisWeek > 0 ? 'up' : 'flat'}
            />
            <KpiCard
              label="Messages delivered"
              value={messagesDelivered}
              trend="up"
            />
            <KpiCard
              label="Blocked users"
              value={data.users.blocked}
              trend="flat"
            />
          </div>

          {/* Zone 2 — 60/40 split */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3">
              <GrowthChart days={data.growth.last_7_days} />
            </div>
            <div className="lg:col-span-2">
              <DeliveryPanel
                rate={data.delivery.sequence_success_rate}
                pending={data.scheduled.pending}
              />
            </div>
          </div>

          {/* Zone 3 — 50/50 split */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <InviteLinksTable links={data.funnels.invite_links} />
            <RecentSends broadcasts={data.broadcasts.recent} />
          </div>
        </div>
      )}
    </div>
  );
}
