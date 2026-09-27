import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiDownload } from "@/lib/api";

export default function RuntimeLogs() {
  const [downloading, setDownloading] = useState(false);

  const downloadLogs = async () => {
    setDownloading(true);
    try {
      await apiDownload("/api/v1/audit/log-files/download", "runtime-logs.zip");
      toast.success("Runtime logs downloaded.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to download runtime logs.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Download Runtime Logs</h1>
        <p className="page-description">
          Download the current JSON Lines logs from the system microservices for offline analysis.
        </p>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Current service logs</CardTitle>
          <CardDescription>
            The ZIP contains one .jsonl file per service, including the API gateway, registry,
            authentication, student, course, and audit services.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={downloadLogs} disabled={downloading}>
            {downloading ? <Loader2 className="animate-spin" /> : <Download />}
            {downloading ? "Preparing download..." : "Download log archive"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
