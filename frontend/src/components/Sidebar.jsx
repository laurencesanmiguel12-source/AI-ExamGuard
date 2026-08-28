import { NavLink } from "react-router-dom";
import { Shield, LayoutDashboard, BookOpen, Layers, GraduationCap, Users, ClipboardList, Award, BarChart3, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useSchool, useSchoolSlug } from "../hooks/useSchoolNav";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "instructor", "student"] },
  { to: "/results", label: "My Results", icon: Award, roles: ["student"] },
  { to: "/courses", label: "Courses", icon: BookOpen, roles: ["admin"] },
  { to: "/subjects", label: "Subjects", icon: Layers, roles: ["admin"] },
  { to: "/students", label: "Students", icon: GraduationCap, roles: ["admin"] },
  { to: "/instructors", label: "Instructors", icon: Users, roles: ["admin"] },
  { to: "/exams", label: "Exams", icon: ClipboardList, roles: ["admin", "instructor"] },
  { to: "/reports", label: "Reports", icon: BarChart3, roles: ["admin", "instructor"] },
];

// Fixed w-56 column on md+ (unchanged behavior); below that it's an off-canvas overlay driven by
// Layout's sidebarOpen state - translate-x-full when closed keeps it out of the way without
// unmounting (no re-fetch of anything nav-related on reopen), a backdrop click or the X closes it.
export default function Sidebar({ open, onClose }) {
  const { user } = useAuth();
  const schoolSlug = useSchoolSlug();
  const school = useSchool();
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user?.role_name));

  return (
    <>
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-full w-64 sm:w-56 flex-col border-r border-border bg-card transition-transform duration-200 md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
            <Shield className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-sm leading-none text-foreground">AI ExamGuard</div>
            <div className="text-muted-foreground text-[9px] font-mono uppercase tracking-[0.2em] truncate">
              {school?.name ?? ""}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="text-muted-foreground hover:text-foreground md:hidden"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4 overflow-y-auto">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={`/${schoolSlug}${to}`}
              onClick={onClose}
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
    </>
  );
}
