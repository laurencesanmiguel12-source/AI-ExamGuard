export default function PreviewBadge({ label = "PREVIEW" }) {
  return (
    <span
      title="Illustrative data — this feature's backend isn't built yet"
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-dashed border-purple-300 bg-purple-50 text-purple-600 text-[9px] font-mono uppercase tracking-widest"
    >
      {label}
    </span>
  );
}
