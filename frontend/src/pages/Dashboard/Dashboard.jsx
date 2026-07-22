import { useAuth } from "../../context/AuthContext";
import StudentDashboard from "./StudentDashboard";
import InstructorDashboard from "./InstructorDashboard";
import AdminDashboard from "./AdminDashboard";

export default function Dashboard() {
  const { user } = useAuth();

  if (user?.role_name === "admin") return <AdminDashboard />;
  if (user?.role_name === "instructor") return <InstructorDashboard />;
  return <StudentDashboard />;
}
