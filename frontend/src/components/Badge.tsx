interface Props {
  label: string;
  variant?: 'green' | 'red' | 'yellow' | 'blue' | 'gray';
}

const variants: Record<string, string> = {
  green: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  red: 'bg-red-500/15 text-red-400 border-red-500/20',
  yellow: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
  blue: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
  gray: 'bg-[#1a2e24] text-[#8aab96] border-[#2a3e34]',
};

export default function Badge({ label, variant = 'gray' }: Props) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${variants[variant]}`}>
      {label}
    </span>
  );
}
