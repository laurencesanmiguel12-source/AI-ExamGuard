import Modal from "./Modal";

/**
 * The read-only "who is this" dialog behind a clickable row.
 *
 * The defense panel asked for it on both list pages - "clicking the student name should show all
 * the details about the student and their subject and course", and for an instructor "how many
 * course and subject and student the instructor has". Rows previously carried Edit and Delete and
 * nothing else, so the only way to see what a record actually contained was to open the edit form
 * and read it out of the inputs - which invites accidental changes just to answer a question.
 *
 * Deliberately read-only, and deliberately shared: two pages asking the same question of two
 * different entities should not grow two different-looking answers.
 */
export default function DetailModal({ title, subtitle, stats = [], sections = [], onClose }) {
  return (
    <Modal title={title} onClose={onClose}>
      {subtitle && <p className="-mt-1 mb-4 text-sm text-muted-foreground">{subtitle}</p>}

      {stats.length > 0 && (
        <div className="mb-5 grid grid-cols-3 gap-2">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-border bg-secondary/40 p-3 text-center">
              <div className="font-display text-2xl font-black text-foreground tabular-nums">
                {s.value}
              </div>
              <div className="mt-0.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-5">
        {sections.map((section) => (
          <div key={section.label}>
            <div className="mb-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
              {section.label}
            </div>

            {section.rows && (
              <dl className="space-y-1.5">
                {section.rows.map(([term, value]) => (
                  <div key={term} className="flex justify-between gap-4 text-sm">
                    <dt className="text-muted-foreground">{term}</dt>
                    <dd className="min-w-0 truncate text-right text-foreground/90">{value ?? "—"}</dd>
                  </div>
                ))}
              </dl>
            )}

            {section.items && (
              section.items.length === 0 ? (
                // Says what the absence means rather than leaving a blank space the reader has to
                // interpret - "none assigned" and "failed to load" look identical otherwise.
                <p className="text-sm text-muted-foreground">{section.emptyLabel ?? "None."}</p>
              ) : (
                <ul className="space-y-1.5">
                  {section.items.map((item) => (
                    <li
                      key={item.key}
                      className="flex items-baseline justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2"
                    >
                      <span className="min-w-0 truncate text-sm text-foreground">{item.primary}</span>
                      {item.secondary && (
                        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                          {item.secondary}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )
            )}
          </div>
        ))}
      </div>
    </Modal>
  );
}
