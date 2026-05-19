interface Props {
  title: string;
  description?: string;
}

export default function EmptyState({ title, description }: Props) {
  return (
    <div className="text-center py-16">
      <p className="text-[#4a7060] font-medium">{title}</p>
      {description && <p className="text-[#2a4030] text-sm mt-1">{description}</p>}
    </div>
  );
}
