import { useMemo, useState } from "react";
import { Edit2, Trash2, Search, X } from "lucide-react";
import Card from "./ui/Card";

// What a row's text is, for searching. Uses each column's own `search` accessor when given, then
// falls back to the raw field - never to col.render, which returns JSX and would match on markup
// rather than on what the reader can actually see.
function rowText(row, columns) {
  return columns
    .map((col) => {
      if (col.search) return col.search(row);
      const value = row[col.key];
      return value === null || value === undefined ? "" : String(value);
    })
    .join(" ")
    .toLowerCase();
}

/**
 * The shared list surface for every module.
 *
 * Two things the defense panel asked for land here rather than in five separate pages, because
 * every list in the app renders through this one component:
 *
 *   "Search function for each module" - there was no search anywhere. Fine at three students,
 *   unusable at three hundred.
 *
 *   "Clicking on the row … should pop out a modal that contains the details" - rows carried Edit
 *   and Delete buttons and nothing else; the row itself was inert.
 *
 * Both are opt-in. A caller that passes neither `searchable` nor `onRowClick` renders exactly what
 * it rendered before.
 */
export default function DataTable({
  columns,
  rows,
  loading,
  emptyLabel = "No records yet.",
  emptyHint,
  emptyAction,
  onEdit,
  onDelete,
  onRowClick,
  searchable = false,
  searchPlaceholder = "Search…",
}) {
  const [query, setQuery] = useState("");

  const visibleRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    // Every whitespace-separated term must match somewhere in the row, so "ana cs-101" narrows
    // rather than widening the way a single substring match would.
    const terms = needle.split(/\s+/);
    return rows.filter((row) => {
      const haystack = rowText(row, columns);
      return terms.every((term) => haystack.includes(term));
    });
  }, [rows, columns, query]);

  const filtered = query.trim().length > 0;

  return (
    <Card>
      {searchable && (
        <div className="border-b border-border px-6 py-3">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/40 focus:outline-none"
            />
            {filtered && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1 text-muted-foreground transition-colors hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          {filtered && (
            // aria-live so the count is announced - a sighted user sees the list shrink, a screen
            // reader user otherwise gets no feedback that typing did anything at all.
            <p aria-live="polite" className="mt-2 text-[11px] font-mono text-muted-foreground">
              {visibleRows.length} of {rows.length} shown
            </p>
          )}
        </div>
      )}

      <div
        className="grid gap-4 px-6 py-2.5 text-[10px] font-mono text-muted-foreground uppercase tracking-widest"
        style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr) auto` }}
      >
        {columns.map((col) => (
          <span key={col.key}>{col.label}</span>
        ))}
        <span>Actions</span>
      </div>
      <div className="divide-y divide-border">
        {loading && <div className="px-6 py-6 text-sm text-muted-foreground">Loading…</div>}

        {/* A search that matches nothing is a different situation from a list that is genuinely
            empty, and telling someone "no records yet" when they simply mistyped sends them off
            to create a duplicate of something that already exists. */}
        {!loading && rows.length > 0 && visibleRows.length === 0 && (
          <div className="px-6 py-10 text-center">
            <p className="text-sm font-medium text-foreground">No matches for “{query.trim()}”</p>
            <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
              {rows.length} record{rows.length === 1 ? "" : "s"} in this list — none of them match
              what you typed.
            </p>
            {/* Not another "Clear search": the X in the field above already has that name, and
                two controls sharing one accessible name is ambiguous to anyone navigating by
                label. This one says what you get instead of what it undoes. */}
            <button
              onClick={() => setQuery("")}
              className="mt-4 rounded-xl border border-border px-4 py-2 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
            >
              Show all {rows.length} record{rows.length === 1 ? "" : "s"}
            </button>
          </div>
        )}

        {/* An empty table is where a new user spends their first minute, so it says what this
            list is for and what to do next rather than only that it is empty. emptyHint and
            emptyAction are optional - a list that genuinely needs no explanation still renders
            just the one line it always did. */}
        {!loading && rows.length === 0 && (
          <div className="px-6 py-10 text-center">
            <p className="text-sm font-medium text-foreground">{emptyLabel}</p>
            {emptyHint && (
              <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">{emptyHint}</p>
            )}
            {emptyAction && <div className="mt-4 flex justify-center">{emptyAction}</div>}
          </div>
        )}

        {!loading &&
          visibleRows.map((row) => (
            <div
              key={row.id}
              // A real button, not a div with onClick: a clickable row has to be reachable by Tab
              // and activated by Enter or Space, and only a button gets all of that for free.
              // Rendered as a plain row when the caller passes no handler, so nothing announces
              // itself as interactive when it is not.
              {...(onRowClick
                ? {
                    role: "button",
                    tabIndex: 0,
                    onClick: () => onRowClick(row),
                    onKeyDown: (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    },
                  }
                : {})}
              className={`grid gap-4 px-6 py-3 items-center transition-colors hover:bg-secondary/50 ${
                onRowClick
                  ? "cursor-pointer focus:bg-secondary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  : ""
              }`}
              style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr) auto` }}
            >
              {columns.map((col) => (
                <span key={col.key} className="text-sm text-foreground/80 truncate">
                  {col.render ? col.render(row) : row[col.key]}
                </span>
              ))}
              {/* stopPropagation, or clicking Delete on a clickable row would also open the
                  detail modal behind the confirmation. */}
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                {onEdit && (
                  <button
                    onClick={() => onEdit(row)}
                    className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded-lg"
                    aria-label="Edit"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => onDelete(row)}
                    className="text-muted-foreground hover:text-red-700 transition-colors p-1.5 rounded-lg"
                    aria-label="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
      </div>
    </Card>
  );
}
