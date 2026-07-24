import { NavLink } from "react-router-dom";
import { Shield, LayoutDashboard, BookOpen, Layers, GraduationCap, Users, ClipboardList, Award, BarChart3 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "instructor", "student"] },
  { to: "/results", label: "My Results", icon: Award, roles: ["student"] },
  { to: "/courses", label: "Courses", icon: BookOpen, roles: ["admin"] },
  { to: "/subjects", label: "Subjects", icon: Layers, roles: ["admin"] },
  { to: "/students", label: "Students", icon: GraduationCap, roles: ["admin"] },
  { to: "/instructors", label: "Instructors", icon: Users, roles: ["admin"] },
  { to: "/exams", label: "Exams", icon: ClipboardList, roles: ["instructor"] },
  { to: "/reports", label: "Reports", icon: BarChart3, roles: ["instructor"] },
];

export default function Sidebar() {
  const { user } = useAuth();
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user?.role_name));

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border">
        <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
          <Shield className="w-3.5 h-3.5 text-white" />
        </div>
        <div>
          <div className="font-display font-bold text-sm leading-none text-foreground">AI ExamGuard</div>
          <div className="text-muted-foreground text-[9px] font-mono uppercase tracking-[0.2em]">
            Arellano University
          </div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-[12px] font-mono uppercase tracking-wider transition-all ${
                isActive
                  ? "bg-primary text-white"
                  : "text-muted-foreground hover:text-foreground hover:bg-black/5"
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
