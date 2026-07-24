import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Landing from "./pages/Landing/Landing";
import Login from "./pages/Login/Login";
import Dashboard from "./pages/Dashboard/Dashboard";
import Courses from "./pages/Courses/Courses";
import Subjects from "./pages/Subjects/Subjects";
import Students from "./pages/Students/Students";
import Instructors from "./pages/Instructors/Instructors";
import Exams from "./pages/Exams/Exams";
import ExamContent from "./pages/ExamContent/ExamContent";
import ExamRoom from "./pages/ExamRoom/ExamRoom";
import Results from "./pages/Results/Results";
import ResultDetail from "./pages/Results/ResultDetail";
import Reports from "./pages/Reports/Reports";
import FaceEnrollment from "./pages/FaceEnrollment/FaceEnrollment";

const EXAM_CONTENT_ROLES = ["instructor"];

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute allowedRoles={["student"]} />}>
            <Route path="/take-exam/:examId" element={<ExamRoom />} />
            <Route path="/face-enrollment" element={<FaceEnrollment />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />

              <Route element={<ProtectedRoute allowedRoles={["student"]} />}>
                <Route path="/results" element={<Results />} />
                <Route path="/results/:sessionId" element={<ResultDetail />} />
              </Route>

              <Route element={<ProtectedRoute allowedRoles={EXAM_CONTENT_ROLES} />}>
                <Route path="/exams" element={<Exams />} />
                <Route path="/exams/:examId/content" element={<ExamContent />} />
                <Route path="/reports" element={<Reports />} />
              </Route>

              <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
                <Route path="/courses" element={<Courses />} />
                <Route path="/subjects" element={<Subjects />} />
                <Route path="/students" element={<Students />} />
                <Route path="/instructors" element={<Instructors />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
