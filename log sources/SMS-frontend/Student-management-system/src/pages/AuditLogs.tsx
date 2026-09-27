import { useState, useEffect } from "react";
import { Search, FileText, Filter, Server, Globe, Mail, AlertCircle, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiGet } from "@/lib/api";

interface AuditLog {
  id: number;
  adminEmail: string;
  action: string;
  serviceName: string;
  targetEntity: string;
  targetId: string;
  details: string;
  ipAddress: string;
  status: "SUCCESS" | "FAILURE";
  errorMessage: string | null;
  createdAt: string;
}

const entityColors: Record<string, string> = {
  STUDENT: "bg-blue-100 text-blue-800 border-blue-200",
  COURSE: "bg-green-100 text-green-800 border-green-200",
  ENROLLMENT: "bg-purple-100 text-purple-800 border-purple-200",
  ADMIN: "bg-orange-100 text-orange-800 border-orange-200",
  SYSTEM: "bg-gray-100 text-gray-800 border-gray-200",
};

export default function AuditLogs() {
  const [searchQuery, setSearchQuery] = useState("");
  const [entityFilter, setEntityFilter] = useState<string>("all");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const data = await apiGet<AuditLog[]>("/api/v1/audit/all");
        setAuditLogs(data);
      } catch {
        // API not connected – leave empty
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  const filteredLogs = auditLogs.filter((log) => {
    const searchLower = searchQuery.toLowerCase();
    const matchesSearch =
      log.action.toLowerCase().includes(searchLower) ||
      (log.details && log.details.toLowerCase().includes(searchLower)) ||
      log.adminEmail.toLowerCase().includes(searchLower) ||
      (log.targetId && log.targetId.toLowerCase().includes(searchLower));

    const matchesEntity = entityFilter === "all" || log.targetEntity === entityFilter;
    return matchesSearch && matchesEntity;
  });

  const formatDateTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return {
      date: date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
      time: date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    };
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Audit Logs</h1>
        <p className="page-description">
          Monitor administrative activities across services. All actions are logged for security and compliance.
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by action, email, target ID, or details..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            {/* <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={entityFilter} onValueChange={setEntityFilter}>
                  <SelectTrigger className="w-44">
                    <SelectValue placeholder="Filter by Entity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Entities</SelectItem>
                    <SelectItem value="STUDENT">Student</SelectItem>
                    <SelectItem value="COURSE">Course</SelectItem>
                    <SelectItem value="ENROLLMENT">Enrollment</SelectItem>
                    <SelectItem value="ADMIN">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div> */}
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Recent Activity
            </div>
            <Badge variant="outline" className="font-normal">
              {filteredLogs.length} Records Found
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action &amp; Service</th>
                  <th>Administrator</th>
                  <th>Target Info</th>
                  <th>Status</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12">
                      <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <Loader2 className="h-8 w-8 animate-spin" />
                        <p>Fetching activity logs...</p>
                      </div>
                    </td>
                  </tr>
                ) : filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <AlertCircle className="h-8 w-8 opacity-20" />
                        <p>No activity logs found matching your criteria.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => {
                    const { date, time } = formatDateTime(log.createdAt);
                    const isSuccess = log.status === "SUCCESS";

                    return (
                      <tr key={log.id} className="group hover:bg-muted/30 transition-colors">
                        <td className="whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="font-medium text-sm">{date}</span>
                            <span className="text-xs text-muted-foreground">{time}</span>
                          </div>
                        </td>
                        <td>
                          <div className="flex flex-col gap-1">
                            <span className="font-bold text-sm tracking-tight">{log.action}</span>
                            <div className="flex items-center gap-1.5 text-[10px] uppercase font-semibold text-muted-foreground">
                              <Server className="h-3 w-3" />
                              {log.serviceName || "Unknown Service"}
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-1.5 text-sm">
                              <Mail className="h-3 w-3 text-muted-foreground" />
                              {log.adminEmail}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <Globe className="h-3 w-3" />
                              {log.ipAddress || "Internal"}
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="flex flex-col gap-1.5">
                            <Badge
                              variant="outline"
                              className={`w-fit text-[10px] px-1.5 py-0 uppercase border ${entityColors[log.targetEntity] || "bg-gray-100 text-gray-800 border-gray-200"}`}
                            >
                              {log.targetEntity || "System"}
                            </Badge>
                            {log.targetId && (
                              <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded border border-border/50 w-fit">
                                {log.targetId}
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          {isSuccess ? (
                            <div className="flex items-center gap-1.5 text-green-600 font-medium text-xs">
                              <CheckCircle2 className="h-4 w-4" />
                              SUCCESS
                            </div>
                          ) : (
                            <div className="flex flex-col gap-1">
                              <div className="flex items-center gap-1.5 text-destructive font-medium text-xs">
                                <XCircle className="h-4 w-4" />
                                FAILURE
                              </div>
                              {log.errorMessage && (
                                <span className="text-[10px] text-destructive/80 leading-tight max-w-[150px] italic">
                                  {log.errorMessage}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="max-w-[200px]">
                          <p className="text-xs text-muted-foreground line-clamp-2" title={log.details || ""}>
                            {log.details || "No additional records"}
                          </p>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <p className="text-[10px] text-muted-foreground mt-6 text-center italic">
        * Audit trails are immutable records for compliance and security auditing.
      </p>
    </div>
  );
}