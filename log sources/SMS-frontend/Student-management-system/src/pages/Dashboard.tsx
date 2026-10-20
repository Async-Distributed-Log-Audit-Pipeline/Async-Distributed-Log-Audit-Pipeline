import { useState, useEffect } from "react";
import { Users, BookOpen, ClipboardList, FileText, TrendingUp, Calendar, ShieldCheck, UserCog, ShieldPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { apiGet } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DashboardStats {
  totalStudents: number | null;
  activeCourses: number | null;
  totalEnrollments: number | null;
  auditActions: number | null;
}

interface RecentAction {
  action: string;
  details: string;
  timestamp: string;
  administrator: string;
}

// ─── Each microservice returns a count wrapper ────────────────────────────────

interface CountResponse {
  count: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const [stats, setStats] = useState<DashboardStats>({
    totalStudents: null,
    activeCourses: null,
    totalEnrollments: null,
    auditActions: null,
  });

  const [recentActions, setRecentActions] = useState<RecentAction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);

      // ── Fire all 5 microservice calls in parallel ──────────────────────────
      // Promise.allSettled ensures one failure doesn't block the rest
      const [
        studentsResult,
        coursesResult,
        enrollmentsResult,
        auditCountResult,
        auditLogsResult,
      ] = await Promise.allSettled([
        // 1. Students Service  →  GET /api/v1/students/count
        apiGet<CountResponse>("/api/v1/student/count"),

        // 2. Courses Service   →  GET /api/v1/courses/count?status=active
        apiGet<CountResponse>("/api/v1/course/count"),

        // 3. Enrollments Service  →  GET /api/v1/enrollments/count
        apiGet<CountResponse>("/api/v1/course/enrollment-count"),

        // 4. Audit Service  →  GET /api/v1/audit/count
        apiGet<CountResponse>("/api/v1/audit/count"),

        // 5. Audit Service  →  GET /api/v1/audit/all?limit=5  (Recent Activity)
        apiGet<RecentAction[]>("/api/v1/audit/all-logs?limit=5"),
      ]);

      // ── Safely extract values (null if service failed or returned unexpected shape) ──
      const safeCount = (result: PromiseSettledResult<any>): number | null => {
        if (result.status !== "fulfilled") return null;
        const value = result.value;
        // Backend returns a plain number directly
        if (typeof value === "number") return value;
        // Fallback: wrapped object shape { count: n }
        if (typeof value?.count === "number") return value.count;
        return null;
      };

      setStats({
        totalStudents: safeCount(studentsResult),
        activeCourses: safeCount(coursesResult),
        totalEnrollments: safeCount(enrollmentsResult),
        auditActions: safeCount(auditCountResult),
      });

      if (auditLogsResult.status === "fulfilled") {
        setRecentActions(auditLogsResult.value);
      }

      setLoading(false);
    };

    fetchData();
  }, []);

  // ── Build stat cards — show "—" if a service didn't respond ───────────────
  const statCards = [
    {
      name: "Total Students",
      value: stats.totalStudents !== null ? stats.totalStudents.toLocaleString() : "—",
      icon: Users,
    },
    {
      name: "Active Courses",
      value: stats.activeCourses !== null ? stats.activeCourses.toLocaleString() : "—",
      icon: BookOpen,
    },
    {
      name: "Enrollments",
      value: stats.totalEnrollments !== null ? stats.totalEnrollments.toLocaleString() : "—",
      icon: ClipboardList,
    },
    {
      name: "Audit Actions",
      value: stats.auditActions !== null ? stats.auditActions.toLocaleString() : "—",
      icon: FileText,
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-description">
          Welcome back, Administrator. Here's an overview of the system.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-16 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))
          : statCards.map((stat) => (
            <Card key={stat.name}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{stat.name}</p>
                    <p className="stat-value mt-1">{stat.value}</p>
                  </div>
                  <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <stat.icon className="h-6 w-6 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-4 mb-8">
        <Button
          onClick={() => { setActiveAction("register"); navigate("/students/register"); }}
          variant={activeAction === "register" ? "default" : "outline"}
          className="h-auto py-4 flex flex-col gap-2"
        >
          <Users className="h-5 w-5" />
          <span>Register Student</span>
        </Button>
        <Button
          onClick={() => { setActiveAction("courses"); navigate("/courses"); }}
          variant={activeAction === "courses" ? "default" : "outline"}
          className="h-auto py-4 flex flex-col gap-2"
        >
          <BookOpen className="h-5 w-5" />
          <span>Manage Courses</span>
        </Button>
        <Button
          onClick={() => { setActiveAction("enrollment"); navigate("/enrollment"); }}
          variant={activeAction === "enrollment" ? "default" : "outline"}
          className="h-auto py-4 flex flex-col gap-2"
        >
          <ClipboardList className="h-5 w-5" />
          <span>Course Enrollment</span>
        </Button>
        <Button
          onClick={() => { setActiveAction("audit"); navigate("/audit-logs"); }}
          variant={activeAction === "audit" ? "default" : "outline"}
          className="h-auto py-4 flex flex-col gap-2"
        >
          <FileText className="h-5 w-5" />
          <span>View Audit Logs</span>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-10 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : recentActions.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
            ) : (
              <div className="space-y-4">
                {recentActions.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 pb-3 border-b border-border last:border-0 last:pb-0"
                  >
                    <div className="h-2 w-2 rounded-full bg-primary mt-2" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{item.action}</p>
                      <p className="text-sm text-muted-foreground truncate">{item.details}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(item.timestamp).toLocaleString()} by {item.administrator}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Admin Management */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Admin Management
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Update your personal information and account settings.
              </p>
              <Button onClick={() => navigate("/admin/profile")} className="w-full" variant="outline">
                <UserCog className="h-4 w-4 mr-2" />
                Manage Profile
              </Button>
            </div>
            <div className="pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground mb-3">
                Register a new administrator account for the system.
              </p>
              <Button onClick={() => navigate("/admin/create")} className="w-full">
                <ShieldPlus className="h-4 w-4 mr-2" />
                Create New Admin
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}





// import { useState, useEffect } from "react";
// import { Users, BookOpen, ClipboardList, FileText, TrendingUp, Calendar } from "lucide-react";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { useNavigate } from "react-router-dom";
// import { apiGet } from "@/lib/api";

// // ─── Types ────────────────────────────────────────────────────────────────────
// interface DashboardStats {
//   totalStudents: number;
//   activeCourses: number;
//   totalEnrollments: number;
//   auditActions: number;
// }

// interface RecentAction {
//   action: string;
//   details: string;
//   timestamp: string;
//   administrator: string;
// }

// // ─── Component ────────────────────────────────────────────────────────────────
// export default function Dashboard() {
//   const navigate = useNavigate();
//   const [activeAction, setActiveAction] = useState<string | null>(null);

//   const [stats, setStats] = useState<DashboardStats | null>(null);
//   const [recentActions, setRecentActions] = useState<RecentAction[]>([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     const fetchData = async () => {
//       setLoading(true);
//       try {
//         // GET YOUR_API_BASE_URL/dashboard/stats
//         const statsData = await apiGet<DashboardStats>("/dashboard/stats");
//         setStats(statsData);

//         // GET YOUR_API_BASE_URL/audit-logs?limit=5
//         const logsData = await apiGet<RecentAction[]>("/api/v1/audit/all?limit=5");
//         setRecentActions(logsData);
//       } catch {
//         // API not connected yet – silently show empty state
//       } finally {
//         setLoading(false);
//       }
//     };
//     fetchData();
//   }, []);

//   const statCards = stats
//     ? [
//       { name: "Total Students", value: stats.totalStudents.toLocaleString(), icon: Users },
//       { name: "Active Courses", value: stats.activeCourses.toLocaleString(), icon: BookOpen },
//       { name: "Enrollments", value: stats.totalEnrollments.toLocaleString(), icon: ClipboardList },
//       { name: "Audit Actions", value: stats.auditActions.toLocaleString(), icon: FileText },
//     ]
//     : [];

//   return (
//     <div className="page-container">
//       <div className="page-header">
//         <h1 className="page-title">Dashboard</h1>
//         <p className="page-description">
//           Welcome back, Administrator. Here's an overview of the system.
//         </p>
//       </div>

//       {/* Stats Grid */}
//       <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
//         {loading
//           ? Array.from({ length: 4 }).map((_, i) => (
//             <Card key={i}>
//               <CardContent className="p-6">
//                 <div className="h-16 bg-muted animate-pulse rounded" />
//               </CardContent>
//             </Card>
//           ))
//           : statCards.map((stat) => (
//             <Card key={stat.name}>
//               <CardContent className="p-6">
//                 <div className="flex items-center justify-between">
//                   <div>
//                     <p className="text-sm font-medium text-muted-foreground">{stat.name}</p>
//                     <p className="stat-value mt-1">{stat.value}</p>
//                   </div>
//                   <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
//                     <stat.icon className="h-6 w-6 text-primary" />
//                   </div>
//                 </div>
//               </CardContent>
//             </Card>
//           ))}
//       </div>

//       {/* Quick Actions */}
//       <div className="grid gap-4 md:grid-cols-4 mb-8">
//         <Button
//           onClick={() => { setActiveAction("register"); navigate("/students/register"); }}
//           variant={activeAction === "register" ? "default" : "outline"}
//           className="h-auto py-4 flex flex-col gap-2"
//         >
//           <Users className="h-5 w-5" />
//           <span>Register Student</span>
//         </Button>
//         <Button
//           onClick={() => { setActiveAction("courses"); navigate("/courses"); }}
//           variant={activeAction === "courses" ? "default" : "outline"}
//           className="h-auto py-4 flex flex-col gap-2"
//         >
//           <BookOpen className="h-5 w-5" />
//           <span>Manage Courses</span>
//         </Button>
//         <Button
//           onClick={() => { setActiveAction("enrollment"); navigate("/enrollment"); }}
//           variant={activeAction === "enrollment" ? "default" : "outline"}
//           className="h-auto py-4 flex flex-col gap-2"
//         >
//           <ClipboardList className="h-5 w-5" />
//           <span>Course Enrollment</span>
//         </Button>
//         <Button
//           onClick={() => { setActiveAction("audit"); navigate("/audit-logs"); }}
//           variant={activeAction === "audit" ? "default" : "outline"}
//           className="h-auto py-4 flex flex-col gap-2"
//         >
//           <FileText className="h-5 w-5" />
//           <span>View Audit Logs</span>
//         </Button>
//       </div>

//       <div className="grid gap-6 lg:grid-cols-2">
//         {/* Recent Activity */}
//         <Card>
//           <CardHeader>
//             <CardTitle className="text-lg flex items-center gap-2">
//               <TrendingUp className="h-5 w-5" />
//               Recent Activity
//             </CardTitle>
//           </CardHeader>
//           <CardContent>
//             {loading ? (
//               <div className="space-y-3">
//                 {Array.from({ length: 4 }).map((_, i) => (
//                   <div key={i} className="h-10 bg-muted animate-pulse rounded" />
//                 ))}
//               </div>
//             ) : recentActions.length === 0 ? (
//               <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
//             ) : (
//               <div className="space-y-4">
//                 {recentActions.map((item, index) => (
//                   <div key={index} className="flex items-start gap-3 pb-3 border-b border-border last:border-0 last:pb-0">
//                     <div className="h-2 w-2 rounded-full bg-primary mt-2" />
//                     <div className="flex-1 min-w-0">
//                       <p className="text-sm font-medium">{item.action}</p>
//                       <p className="text-sm text-muted-foreground truncate">{item.details}</p>
//                       <p className="text-xs text-muted-foreground mt-1">
//                         {new Date(item.timestamp).toLocaleString()} by {item.administrator}
//                       </p>
//                     </div>
//                   </div>
//                 ))}
//               </div>
//             )}
//           </CardContent>
//         </Card>

//         {/* Admin Management */}
//         <Card>
//           <CardHeader>
//             <CardTitle className="text-lg flex items-center gap-2">
//               <Calendar className="h-5 w-5" />
//               Admin Management
//             </CardTitle>
//           </CardHeader>
//           <CardContent>
//             <p className="text-sm text-muted-foreground mb-4">
//               Create a new administrator account for the system.
//             </p>
//             <Button onClick={() => navigate("/admin/create")} className="w-full">
//               <Users className="h-4 w-4 mr-2" />
//               Create New Admin
//             </Button>
//           </CardContent>
//         </Card>
//       </div>
//     </div>
//   );
// }