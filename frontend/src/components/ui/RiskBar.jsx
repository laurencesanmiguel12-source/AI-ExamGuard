export default function RiskBar({ value, showLabel = true }) {
  const color = value < 25 ? "#10b981" : value < 50 ? "#3b82f6" : value < 75 ? "#f97316" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-black/8 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${value}%`, backgroundColor: color, transition: "width 0.8s ease" }}
        />
      </div>
      {showLabel && <span className="font-mono text-[11px] text-muted-foreground w-7 text-right">{value}</span>}
    </div>
  );
}
