import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  BookOpen,
  UserPlus,
  ClipboardList,
  FileText,
  Download,
  GraduationCap,
  Menu,
  X,
  LogOut,
  ShieldPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

// Navigation items
const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Students", href: "/students", icon: Users },
  // { name: "Register Student", href: "/students/register", icon: UserPlus },
  { name: "Courses", href: "/courses", icon: BookOpen },
  { name: "Enrollment", href: "/enrollment", icon: ClipboardList },
  { name: "Audit Logs", href: "/audit-logs", icon: FileText },
  { name: "Download Logs", href: "/runtime-logs", icon: Download },
  { name: "My Profile", href: "/admin/profile", icon: ShieldPlus },
  { name: "Create Admin", href: "/admin/create", icon: UserPlus },
];

export function AdminSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { logout } = useAuth();

  // Decode username from JWT if available
  const getUsername = () => {
    const token = localStorage.getItem("jwt_token");
    if (!token) return "Admin";
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.sub ?? payload.username ?? payload.name ?? "Admin";
    } catch {
      return "Admin";
    }
  };
  const username = getUsername();

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-6 border-b border-sidebar-border">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white p-1">
          <img
            src="/kdu-logo.png"
            alt="KDU Logo"
            className="h-full w-full object-contain"
          />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-sidebar-foreground">KDU</span>
          <span className="text-xs text-white">Student Management</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive =
            location.pathname === item.href ||
            (item.href === "/students" && location.pathname.startsWith("/students/") && location.pathname !== "/students/register" && !location.pathname.endsWith("/edit")) ||
            (item.href === "/students/register" && location.pathname.endsWith("/edit"));
          return (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer with username */}
      <div className="px-4 py-4 border-t border-sidebar-border">
        <div className="text-xs text-white">
          <p>Logged in as </p>
          <p className="mt-1 font-medium">{username}</p>
        </div>
      </div>

      {/* Logout */}
      <div className="px-4 py-4 border-t border-sidebar-border mt-auto">
        <Button
          variant="ghost"
          size="sm"
          className="flex w-full items-center gap-2 text-sidebar-foreground hover:bg-sidebar-accent/50"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 bg-sidebar flex flex-col transform transition-transform duration-200 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <SidebarContent />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-sidebar">
        <SidebarContent />
      </aside>
    </>
  );
}