import { X } from "lucide-react";

interface FilterChipProps {
  label: string;
  onRemove: () => void;
}

export function FilterChip({ label, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded glass text-steel text-xs font-medium hover:text-gray-200 transition-colors">
      {label}
      <button
        onClick={onRemove}
        className="hover:text-accent rounded-full p-0.5 transition-colors"
      >
        <X size={12} />
      </button>
    </span>
  );
}
