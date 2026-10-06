import type { LucideIcon } from "lucide-react";

type Category = "volume" | "warning" | "danger" | "success" | "neutral";

const CATEGORY_BORDER: Record<Category, string> = {
  volume: "border-t-accent",
  warning: "border-t-warning",
  danger: "border-t-danger",
  success: "border-t-success",
  neutral: "border-t-border",
};

const CATEGORY_ICON_COLOR: Record<Category, string> = {
  volume: "text-accent",
  warning: "text-warning",
  danger: "text-danger",
  success: "text-success",
  neutral: "text-text-secondary",
};

export function StatCard({
  label,
  value,
  icon: Icon,
  category = "neutral",
  suffix,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  category?: Category;
  suffix?: string;
}) {
  return (
    <div
      className={`rounded-sm border border-border border-t-2 bg-surface p-4 ${CATEGORY_BORDER[category]}`}
    >
      <div className="flex items-start justify-between">
        <span className="text-xs text-text-secondary">{label}</span>
        <Icon size={15} className={CATEGORY_ICON_COLOR[category]} />
      </div>
      <div className="mt-2 font-mono text-2xl tabular text-text-primary">
        {value}
        {suffix && <span className="ml-1 text-sm text-text-secondary">{suffix}</span>}
      </div>
    </div>
  );
}
