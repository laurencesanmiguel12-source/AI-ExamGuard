import { PieChart as RPie, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

export const VIOLATION_META = {
  TAB_SWITCH: { label: "Tab Switch", fill: "#1a4fa8" },
  FULLSCREEN_EXIT: { label: "Fullscreen Exit", fill: "#c8192e" },
  COPY_PASTE: { label: "Copy/Paste", fill: "#e86e1e" },
  RIGHT_CLICK: { label: "Right Click", fill: "#8b1ec4" },
  FACE_LOST: { label: "Face Lost", fill: "#1ec47a" },
  IDENTITY_MISMATCH: { label: "Identity Mismatch", fill: "#f43f5e" },
  PHONE_DETECTED: { label: "Phone Detected", fill: "#eab308" },
  MULTIPLE_PEOPLE: { label: "Multiple People", fill: "#0ea5e9" },
  AI_TOOL_DETECTED: { label: "AI Tool Detected", fill: "#dc2626" },
  SEARCH_ENGINE_DETECTED: { label: "Search Engine Detected", fill: "#f97316" },
  // Head pose, not eye gaze - a coarse proxy, not a certain detection, so it reads as "needs
  // review" rather than a hard accusation.
  PROLONGED_HEAD_DOWN: { label: "Prolonged Downward Gaze", fill: "#0d9488" },
  // Sustained near-identical webcam frames - a suspected static photo held up to the camera,
  // not just a single bad-angle mismatch. See risk_service.py's weighting note.
  STATIC_IMAGE_SUSPECTED: { label: "Static Image Suspected", fill: "#9333ea" },
};

const TT = { background: "#fff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 8, fontSize: 11, fontFamily: "JetBrains Mono", color: "#0f172a" };
const TT_LABEL = { color: "#64748b" };

// violationCounts: { [event_type]: count }, e.g. RiskService.get_live_sessions' violation_counts,
// or the exam/school report's violation_breakdown - same event_type keys everywhere.
export default function ViolationBreakdownChart({ violationCounts, emptyLabel = "No violations logged yet." }) {
  const breakdown = Object.entries(VIOLATION_META)
    .map(([type, meta]) => ({
      name: meta.label,
      fill: meta.fill,
      value: violationCounts[type] ?? 0,
    }))
    .filter((v) => v.value > 0);

  if (breakdown.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }

  return (
    <>
      <ResponsiveContainer width="100%" height={160}>
        <RPie>
          <Pie data={breakdown} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" paddingAngle={3}>
            {breakdown.map((e, i) => <Cell key={i} fill={e.fill} />)}
          </Pie>
          <Tooltip contentStyle={TT} labelStyle={TT_LABEL} />
        </RPie>
      </ResponsiveContainer>
      <div className="space-y-1.5 mt-1">
        {breakdown.map((v) => (
          <div key={v.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: v.fill }} />
              <span className="text-[11px] text-muted-foreground">{v.name}</span>
            </div>
            <span className="font-mono text-[11px] text-foreground/70">{v.value}</span>
          </div>
        ))}
      </div>
    </>
  );
}
