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
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
