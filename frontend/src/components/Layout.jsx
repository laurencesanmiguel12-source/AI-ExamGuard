import { useCallback, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import IdleLogoutWarningModal from "./IdleLogoutWarningModal";
import useIdleLogout from "../hooks/useIdleLogout";
import { useAuth } from "../context/AuthContext";
import { useSchoolNav } from "../hooks/useSchoolNav";

export default function Layout() {
  // Sidebar is a fixed-width column on md+ viewports (unchanged) but an off-canvas overlay below
  // that - this is the one piece of state both Navbar (the toggle button) and Sidebar (the panel
  // itself) need to share, so it lives here rather than in either.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { logout } = useAuth();
  const navigate = useSchoolNav();

  const handleIdleLogout = useCallback(() => {
    logout();
    navigate("/login");
  }, [logout, navigate]);

  const { warning, stayLoggedIn } = useIdleLogout(handleIdleLogout);

  return (
    <div className="flex h-screen bg-background">
      {warning && (
        <IdleLogoutWarningModal onStayLoggedIn={stayLoggedIn} onLogoutNow={handleIdleLogout} />
      )}
      {/* WCAG 2.4.1 Bypass Blocks (Level A). The sidebar repeats up to nine nav links on every
          screen, so without this a keyboard or screen-reader user tabs through the whole nav
          again on every page load before reaching the content. Visually hidden until focused,
          which is the point - it only needs to exist for the people who tab. An automated audit
          cannot catch this one: it reads as a normal link, and the criterion is about the
          repetition across pages, not the markup of any single one. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-3 focus:left-3 focus:bg-card focus:text-foreground focus:border focus:border-border focus:rounded-xl focus:px-4 focus:py-2 focus:text-sm"
      >
        Skip to main content
      </a>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
