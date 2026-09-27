import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Courses from "./pages/Courses";
import StudentRegistration from "./pages/StudentRegistration";
import StudentEdit from "./pages/StudentEdit";
import StudentList from "./pages/StudentList";
import StudentProfile from "./pages/StudentProfile";
import Enrollment from "./pages/Enrollment";
import AuditLogs from "./pages/AuditLogs";
import NotFound from "./pages/NotFound";
import CreateAdmin from "./pages/CreateAdmin";
import AdminProfile from "./pages/AdminProfile";
import RuntimeLogs from "./pages/RuntimeLogs";

const queryClient = new QueryClient();

// Redirects unauthenticated users to /login
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Login />} />
            <Route path="/login" element={<Login />} />

            {/* Protected admin routes */}
            <Route
              element={
                <PrivateRoute>
                  <AdminLayout />
                </PrivateRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/students" element={<StudentList />} />
              <Route path="/students/register" element={<StudentRegistration />} />
              <Route path="/students/:id" element={<StudentProfile />} />
              <Route path="/students/:id/edit" element={<StudentEdit />} />
              <Route path="/courses" element={<Courses />} />
              <Route path="/enrollment" element={<Enrollment />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/runtime-logs" element={<RuntimeLogs />} />
              {/* Admin management – only accessible when logged in */}
              <Route path="/admin/create" element={<CreateAdmin />} />
              <Route path="/admin/profile" element={<AdminProfile />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
