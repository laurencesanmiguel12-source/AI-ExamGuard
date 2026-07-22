export default function RiskPill({ value }) {
  const cfg =
    value < 25 ? { cls: "bg-emerald-50 text-emerald-700 border-emerald-200", label: "LOW" }
    : value < 50 ? { cls: "bg-blue-50 text-blue-700 border-blue-200", label: "MEDIUM" }
    : value < 75 ? { cls: "bg-orange-50 text-orange-700 border-orange-200", label: "HIGH" }
    : { cls: "bg-red-50 text-red-700 border-red-200", label: "CRITICAL" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[10px] font-mono font-bold tracking-widest ${cfg.cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {cfg.label} · {value}
    </span>
  );
}
