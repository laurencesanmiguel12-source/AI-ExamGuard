import { LogOut, Menu } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useSchoolNav } from "../hooks/useSchoolNav";

export default function Navbar({ onMenuClick }) {
  const { user, logout } = useAuth();
  const navigate = useSchoolNav();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4 sm:px-6 gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          aria-label="Open menu"
          className="text-muted-foreground hover:text-foreground md:hidden flex-shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="text-sm text-muted-foreground truncate">
          <span className="hidden sm:inline">Welcome, </span>
          <span className="font-medium text-foreground">{user?.first_name}</span>
          <span className="ml-2 rounded border border-border bg-secondary px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
            {user?.role_name}
          </span>
        </div>
      </div>
      {/* aria-label, even though the button has visible text: that text is `hidden sm:inline`, so
          below 640px it collapses to a bare icon with no accessible name at all - the button
          simply announces as "button". Caught by Lighthouse, which audits at a mobile viewport by
          default and so sees the state a desktop check never does. The label is duplicated by the
          visible text at wider widths, which is harmless - it wins over the text content either
          way and says the same thing. */}
      <button
        onClick={handleLogout}
        aria-label="Log out"
        className="flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors flex-shrink-0"
      >
        <LogOut className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Log out</span>
      </button>
    </header>
  );
}
