import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Pencil, Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPut } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DegreeProgramOption {
  name: string;
  displayName: string;
  code: string;
}

const FALLBACK_DEGREE_PROGRAMS: DegreeProgramOption[] = [
  { name: "SOFTWARE_ENGINEERING", displayName: "Software Engineering", code: "SE" },
  { name: "COMPUTER_ENGINEERING", displayName: "Computer Engineering", code: "CE" },
  { name: "COMPUTER_SCIENCE", displayName: "Computer Science", code: "CS" },
  { name: "INFORMATION_TECHNOLOGY", displayName: "Information Technology", code: "IT" },
  { name: "DATA_SCIENCE", displayName: "Data Science", code: "DBA" },
];

enum StudentStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
  GRADUATED = "GRADUATED",
  WITHDRAWN = "WITHDRAWN",
  TRANSFERRED = "TRANSFERRED",
  SUSPENDED = "SUSPENDED",
}

const STUDENT_STATUS_OPTIONS = [
  { value: StudentStatus.ACTIVE, label: "Active" },
  { value: StudentStatus.INACTIVE, label: "Inactive" },
  { value: StudentStatus.GRADUATED, label: "Graduated" },
  { value: StudentStatus.WITHDRAWN, label: "Withdrawn" },
  { value: StudentStatus.TRANSFERRED, label: "Transferred" },
  { value: StudentStatus.SUSPENDED, label: "Suspended" },
];

interface FormData {
  studentIdNumber: string;
  firstName: string;
  lastName: string;
  intake: string;
  address: string;
  birthday: string;
  degreeProgram: string;
  status: string;
}

interface FormErrors {
  studentIdNumber: string;
  firstName: string;
  lastName: string;
  intake: string;
  address: string;
  birthday: string;
  degreeProgram: string;
  status: string;
}

const emptyForm: FormData = {
  studentIdNumber: "",
  firstName: "",
  lastName: "",
  intake: "",
  address: "",
  birthday: "",
  degreeProgram: "",
  status: "",
};

const emptyErrors: FormErrors = { ...emptyForm };

// ─── Component ────────────────────────────────────────────────────────────────

export default function StudentEdit() {
  const navigate = useNavigate();
  const { id } = useParams(); // This is the studentNumber identifier

  const [formData, setFormData] = useState<FormData>(emptyForm);
  const [errors, setErrors] = useState<FormErrors>(emptyErrors);
  const [loading, setLoading] = useState(false);
  const [fetchingStudent, setFetchingStudent] = useState(true);
  const [degreePrograms, setDegreePrograms] = useState<DegreeProgramOption[]>(FALLBACK_DEGREE_PROGRAMS);
  const [degreeProgramsReady, setDegreeProgramsReady] = useState(false);

  // ── Load degree programs ───────────────────────────────────────────────────
  useEffect(() => {
    const fetchDegreePrograms = async () => {
      try {
        const data = await apiGet<DegreeProgramOption[] | string[]>("/api/v1/students/degree-programs");
        if (Array.isArray(data) && data.length > 0) {
          if (typeof data[0] === "string") {
            const mapped = (data as string[]).map((name) => {
              const fallback = FALLBACK_DEGREE_PROGRAMS.find((f) => f.name === name);
              return fallback ?? { name, displayName: name.replace(/_/g, " "), code: "" };
            });
            setDegreePrograms(mapped);
          } else {
            setDegreePrograms(data as DegreeProgramOption[]);
          }
        }
      } catch {
        // Fallback already set
      } finally {
        setDegreeProgramsReady(true);
      }
    };
    fetchDegreePrograms();
  }, []);

  // ── Pre-fill student data ──────────────────────────────────────────────────
  useEffect(() => {
    if (!id || !degreeProgramsReady) return;

    const fetchStudent = async () => {
      setFetchingStudent(true);
      try {
        const data = await apiGet<any>(`/api/v1/student/get-every-student-details/${id}`);
        setFormData({
          studentIdNumber: data.studentIdNumber ?? "",
          firstName: data.firstName ?? "",
          lastName: data.lastName ?? "",
          intake: data.intake != null ? String(data.intake) : "",
          address: data.address ?? "",
          birthday: data.birthday ?? "",
          degreeProgram: data.degreeProgram != null ? String(data.degreeProgram) : "",
          status: data.status ?? "",
        });
      } catch {
        toast.error("Failed to load student data");
        navigate("/students");
      } finally {
        setFetchingStudent(false);
      }
    };
    fetchStudent();
  }, [id, degreeProgramsReady, navigate]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = { ...emptyErrors };
    if (!formData.studentIdNumber.trim()) newErrors.studentIdNumber = "Student ID is required";
    if (!formData.firstName.trim()) newErrors.firstName = "First name is required";
    if (!formData.lastName.trim()) newErrors.lastName = "Last name is required";
    if (!formData.intake.trim()) {
      newErrors.intake = "Intake year is required";
    } else if (!/^\d{2}$/.test(formData.intake)) {
      newErrors.intake = "Intake must be a 2-digit year";
    }
    if (!formData.address.trim()) newErrors.address = "Address is required";
    if (!formData.birthday) newErrors.birthday = "Date of birth is required";
    if (!formData.degreeProgram) newErrors.degreeProgram = "Degree program is required";
    if (!formData.status) newErrors.status = "Student status is required";

    setErrors(newErrors);
    return Object.values(newErrors).every((e) => !e);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    const payload = {
      studentIdNumber: formData.studentIdNumber,
      firstName: formData.firstName,
      lastName: formData.lastName,
      intake: parseInt(formData.intake, 10),
      address: formData.address,
      birthday: formData.birthday,
      degreeProgram: formData.degreeProgram,
      status: formData.status,
    };

    try {
      // Use specific update API
      await apiPut(`/api/v1/student/update-student-details/${id}`, payload);
      toast.success("Student updated successfully");
      navigate("/students");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Update failed";
      toast.error("Failed to update student", { description: msg });
    } finally {
      setLoading(false);
    }
  };

  if (fetchingStudent) {
    return (
      <div className="page-container">
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin mr-2" />
          Loading student data…
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Button variant="ghost" onClick={() => navigate("/students")} className="mb-4 p-0 hover:bg-transparent">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Students
        </Button>
        <h1 className="page-title">Edit Student</h1>
        <p className="page-description">Update the student's personal and academic details.</p>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Pencil className="h-5 w-5" />
            Edit Student Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="form-section">
            <div className="input-wrapper">
              <Label htmlFor="studentIdNumber">Student ID Number</Label>
              <Input
                id="studentIdNumber"
                value={formData.studentIdNumber}
                onChange={(e) => setFormData({ ...formData, studentIdNumber: e.target.value })}
                disabled={true} // ID usually not changeable
              />
            </div>

            <div className="form-row">
              <div className="input-wrapper">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                  disabled={loading}
                />
                {errors.firstName && <p className="validation-message">{errors.firstName}</p>}
              </div>
              <div className="input-wrapper">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                  disabled={loading}
                />
                {errors.lastName && <p className="validation-message">{errors.lastName}</p>}
              </div>
            </div>

            <div className="input-wrapper">
              <Label htmlFor="intake">Intake</Label>
              <Input
                id="intake"
                value={formData.intake}
                onChange={(e) => setFormData({ ...formData, intake: e.target.value })}
                disabled={loading}
              />
              {errors.intake && <p className="validation-message">{errors.intake}</p>}
            </div>

            <div className="input-wrapper">
              <Label htmlFor="address">Address</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                disabled={loading}
              />
              {errors.address && <p className="validation-message">{errors.address}</p>}
            </div>

            <div className="form-row">
              <div className="input-wrapper">
                <Label htmlFor="birthday">Date of Birth</Label>
                <Input
                  id="birthday"
                  type="date"
                  value={formData.birthday}
                  onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
                  disabled={loading}
                />
                {errors.birthday && <p className="validation-message">{errors.birthday}</p>}
              </div>

              <div className="input-wrapper">
                <Label htmlFor="degreeProgram">Degree Program</Label>
                <Select
                  value={formData.degreeProgram}
                  onValueChange={(value) => setFormData({ ...formData, degreeProgram: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="degreeProgram">
                    <SelectValue placeholder="Select degree program" />
                  </SelectTrigger>
                  <SelectContent>
                    {degreePrograms.map((program) => (
                      <SelectItem key={program.name} value={program.name}>
                        {program.displayName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.degreeProgram && <p className="validation-message">{errors.degreeProgram}</p>}
              </div>
            </div>

            <div className="input-wrapper">
              <Label htmlFor="status">Student Status</Label>
              <Select
                value={formData.status}
                onValueChange={(value) => setFormData({ ...formData, status: value })}
                disabled={loading}
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select student status" />
                </SelectTrigger>
                <SelectContent>
                  {STUDENT_STATUS_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.status && <p className="validation-message">{errors.status}</p>}
            </div>

            <div className="flex gap-3 pt-4">
              <Button type="submit" disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Changes
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate("/students")}
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
