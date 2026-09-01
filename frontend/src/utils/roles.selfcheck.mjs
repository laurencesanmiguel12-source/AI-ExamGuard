// Zero-dependency self-check for roles.js - the frontend has no test runner and this helper is not
// worth adding one for. Run it directly:  node src/utils/roles.selfcheck.mjs
//
// Guards the super-admin lockout: every gate compared role_name to the literal "admin", so a super
// admin got an empty sidebar, was bounced off every page by ProtectedRoute, and fell through
// Dashboard's role switch onto the student dashboard.
import assert from "node:assert/strict";
import { isAdmin, hasRole } from "./roles.js";

const superAdmin = { role_name: "super_admin" };
const admin = { role_name: "admin" };
const instructor = { role_name: "instructor" };
const student = { role_name: "student" };

// A super admin counts as an admin, everywhere.
assert.equal(isAdmin(superAdmin), true);
assert.equal(isAdmin(admin), true);
assert.equal(isAdmin(instructor), false);
assert.equal(isAdmin(student), false);
assert.equal(isAdmin(null), false);
assert.equal(isAdmin(undefined), false);

// The actual lockout: these are the real allowedRoles/nav lists from App.jsx and Sidebar.jsx.
assert.equal(hasRole(superAdmin, ["admin"]), true, "super admin was locked out of admin-only pages");
assert.equal(hasRole(superAdmin, ["admin", "instructor"]), true);
assert.equal(hasRole(admin, ["admin"]), true);
assert.equal(hasRole(instructor, ["admin", "instructor"]), true);

// A list that does NOT name "admin" must not start matching admins - student and instructor pages
// depend on a linked profile row that an admin/super admin account has no reason to own.
assert.equal(hasRole(superAdmin, ["student"]), false, "super admin must not reach student-only pages");
assert.equal(hasRole(admin, ["student"]), false);
assert.equal(hasRole(superAdmin, ["instructor"]), false);
assert.equal(hasRole(admin, ["instructor"]), false);

// Roles still gate normally.
assert.equal(hasRole(student, ["admin"]), false);
assert.equal(hasRole(instructor, ["admin"]), false);
assert.equal(hasRole(student, ["student"]), true);
assert.equal(hasRole(null, ["admin"]), false);

console.log("roles.js self-check: all assertions passed");
