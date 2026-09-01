// The backend's require_admin accepts "admin" AND "super_admin" - a super admin can do everything
// a school admin can, for any school (see backend/app/auth/dependencies.py). The frontend never
// mirrored that: every gate compared role_name to the literal "admin", so a super admin got an
// empty sidebar, was bounced off every page by ProtectedRoute, and fell through Dashboard's role
// switch onto the student dashboard. Keep the rule in one place so the next role gate can't drift
// from the backend again.

export const isAdmin = (user) =>
  user?.role_name === "admin" || user?.role_name === "super_admin";

// An allowedRoles/nav list naming "admin" is satisfied by a super admin too. Lists that name
// "instructor" or "student" still match only those roles exactly - a super admin has no linked
// instructor or student profile row, so student/instructor-specific pages would break on it.
export const hasRole = (user, roles) =>
  roles.includes(user?.role_name) || (roles.includes("admin") && isAdmin(user));
