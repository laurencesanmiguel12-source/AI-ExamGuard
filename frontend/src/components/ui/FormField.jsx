import { useId } from "react";

export function TextField({ label, id, ...props }) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  return (
    <div className="mb-4">
      <label htmlFor={fieldId} className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
        {label}
      </label>
      <input
        id={fieldId}
        {...props}
        className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground outline-none focus:border-primary/40 transition-colors"
      />
    </div>
  );
}

export function SelectField({ label, children, id, ...props }) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  return (
    <div className="mb-4">
      <label htmlFor={fieldId} className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
        {label}
      </label>
      <select
        id={fieldId}
        {...props}
        className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground outline-none focus:border-primary/40 transition-colors"
      >
        {children}
      </select>
    </div>
  );
}

export function CheckboxField({ label, ...props }) {
  return (
    <label className="flex items-center gap-2.5 mb-4 cursor-pointer">
      <input type="checkbox" {...props} className="w-4 h-4 accent-primary" />
      <span className="text-sm text-foreground">{label}</span>
    </label>
  );
}
