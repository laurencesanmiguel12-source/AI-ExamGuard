import { Edit2, Trash2 } from "lucide-react";
import Card from "./ui/Card";

export default function DataTable({
  columns,
  rows,
  loading,
  emptyLabel = "No records yet.",
  emptyHint,
  emptyAction,
  onEdit,
  onDelete,
}) {
  return (
    <Card>
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
          rows.map((row) => (
            <div
              key={row.id}
              className="grid gap-4 px-6 py-3 items-center hover:bg-secondary/50 transition-colors"
              style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr) auto` }}
            >
              {columns.map((col) => (
                <span key={col.key} className="text-sm text-foreground/80 truncate">
                  {col.render ? col.render(row) : row[col.key]}
                </span>
              ))}
              <div className="flex items-center gap-2">
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
