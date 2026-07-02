interface Props {
  message: string;
}

export default function ErrorState({ message }: Props) {
  return (
    <div className="text-center py-16">
      <p className="text-red-400 font-medium">Error</p>
      <p className="text-[#4a7060] text-sm mt-1">{message}</p>
    </div>
  );
}
