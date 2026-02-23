import { X } from "lucide-react";

interface FilterChipProps {
  label: string;
  onRemove: () => void;
}

export function FilterChip({ label, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-brand-red/10 text-brand-red-light text-xs font-medium border border-brand-red/20">
      {label}
      <button
        onClick={onRemove}
        className="hover:bg-brand-red/20 rounded-full p-0.5 transition-colors"
      >
        <X size={12} />
      </button>
    </span>
  );
}
