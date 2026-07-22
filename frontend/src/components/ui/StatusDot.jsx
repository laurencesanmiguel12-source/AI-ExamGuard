export default function StatusDot({ on, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${on ? "bg-emerald-500" : "bg-red-500"}`} />
      <span className="text-[11px] font-mono text-muted-foreground">{label}</span>
    </div>
  );
}
