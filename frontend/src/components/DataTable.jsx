import { Edit2, Trash2 } from "lucide-react";
import Card from "./ui/Card";

export default function DataTable({ columns, rows, loading, emptyLabel = "No records yet.", onEdit, onDelete }) {
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
        {!loading && rows.length === 0 && (
          <div className="px-6 py-6 text-sm text-muted-foreground">{emptyLabel}</div>
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
