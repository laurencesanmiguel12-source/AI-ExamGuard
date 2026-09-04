import { useId } from "react";

// `hint` is one line of plain-language help under the field, wired to the input with
// aria-describedby so screen readers announce it as part of the field rather than as stray
// text. Use it wherever the label alone leaves someone guessing - "Passing Score" out of
// what, what a "Code" should look like - not to restate the label.
export function TextField({ label, id, hint, ...props }) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const hintId = `${fieldId}-hint`;
  return (
    <div className="mb-4">
      <label htmlFor={fieldId} className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
        {label}
      </label>
      <input
        id={fieldId}
        aria-describedby={hint ? hintId : undefined}
        {...props}
        className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground outline-none focus:border-primary/40 transition-colors"
      />
      {hint && (
        <p id={hintId} className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  );
}

export function SelectField({ label, children, id, hint, ...props }) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const hintId = `${fieldId}-hint`;
  return (
    <div className="mb-4">
      <label htmlFor={fieldId} className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest block mb-1.5">
        {label}
      </label>
      <select
        id={fieldId}
        aria-describedby={hint ? hintId : undefined}
        {...props}
        className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground outline-none focus:border-primary/40 transition-colors"
      >
        {children}
      </select>
      {hint && (
        <p id={hintId} className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
      )}
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
