export default function SectionTag({ text }) {
  return (
    <div className="inline-flex items-center gap-2 mb-4">
      <div className="w-4 h-px bg-primary" />
      <span className="text-primary text-[11px] font-mono uppercase tracking-[0.2em]">{text}</span>
    </div>
  );
}
