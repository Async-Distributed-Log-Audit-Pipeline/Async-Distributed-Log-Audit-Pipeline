import { useState, useEffect } from "react";
import { Search, Plus, Trash2, Pencil, ClipboardList, User, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";

// const semesters = [
//   { value: "SEMESTER_1", label: "Semester 1" },
//   { value: "SEMESTER_2", label: "Semester 2" },
//   { value: "SUMMER_SEMESTER", label: "Summer Semester" },
// ];

// const statuses = ["ENROLLED", "COMPLETED", "DROPPED", "FAILED"];
// const grades = ["A", "B", "C", "D", "F", "N/A"];

const semesters = [
  { value: "SEMESTER_1", label: "Semester 1" },
  { value: "SEMESTER_2", label: "Semester 2" },
  { value: "SEMESTER_3", label: "Semester 3" },
  { value: "SEMESTER_4", label: "Semester 4" },
  { value: "SEMESTER_5", label: "Semester 5" },
  { value: "SEMESTER_6", label: "Semester 6" },
  { value: "SEMESTER_7", label: "Semester 7" },
  { value: "SEMESTER_8", label: "Semester 8" },
  { value: "SUMMER", label: "Summer Semester" },
];

const statuses = [
  { value: "ENROLLED", label: "Currently Enrolled" },
  { value: "COMPLETED", label: "Completed" },
  { value: "DROPPED", label: "Dropped" },
  { value: "FAILED", label: "Failed" },
  { value: "WITHDRAWN", label: "Withdrawn" },
];

const grades = [
  { value: "A_PLUS", label: "A+" },
  { value: "A", label: "A" },
  { value: "A_MINUS", label: "A-" },
  { value: "B_PLUS", label: "B+" },
  { value: "B", label: "B" },
  { value: "B_MINUS", label: "B-" },
  { value: "C_PLUS", label: "C+" },
  { value: "C", label: "C" },
  { value: "C_MINUS", label: "C-" },
  { value: "D", label: "D" },
  { value: "F", label: "F" },
  { value: "INCOMPLETE", label: "I" },
  { value: "PASS", label: "P" },
  { value: "NOT_GRADED", label: "NG" },
];

interface Student {
  id: string; // from backend (or similar)
  studentId: string; // The primary ID from the student API
  firstName: string;
  lastName: string;
  studentNumber?: string; // Add optional mapping just in case
}

interface Course {
  id: string;
  courseId: string; // Used as courseCode as mapped from backend
  courseName: string;
}

interface Enrollment {
  id: number;
  studentNumber: string;
  course: {
    courseCode: string;
    courseName: string;
  };
  semester: string;
  academicYear: number;
  enrollmentDate: string;
  status: string;
  grade: string;
}

export default function Enrollment() {
  const [searchQuery, setSearchQuery] = useState("");
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loadingEnrollments, setLoadingEnrollments] = useState(false);
  const [saving, setSaving] = useState(false);

  const [isRemoveDialogOpen, setIsRemoveDialogOpen] = useState(false);
  const [selectedEnrollment, setSelectedEnrollment] = useState<Enrollment | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState({ status: "", grade: "" });

  const [enrollForm, setEnrollForm] = useState({
    courseId: "", // this will bind to courseCode
    semester: "",
    academicYear: "",
    enrollmentDate: "",
    credits: "3", // default
  });
  const [errors, setErrors] = useState({
    courseId: "",
    semester: "",
    academicYear: "",
    enrollmentDate: "",
    credits: "",
  });

  // Load students and courses once
  useEffect(() => {
    const init = async () => {
      try {
        // REPLACE THIS with your actual student fetching API
        const s = await apiGet<Student[]>("/api/v1/student/get-all-students");
        setStudents(s);
        const c = await apiGet<Course[]>("/api/v1/course/get-all-courses");
        setCourses(c);
      } catch {
        toast.error("Failed to load global data. Check your API endpoints.");
      }
    };
    init();
  }, []);

  // Function to fetch enrollments for the selected student
  const fetchEnrollmentsForStudent = async (student: Student) => {
    setLoadingEnrollments(true);
    try {
      // Use the same ID logic consistently: student.id || student.studentNumber
      const studentId = student.id || student.studentNumber || student.studentId;
      const data = await apiGet<Enrollment[]>(`/api/v1/course/getEnrollmentByStudentNumber/${studentId}`);
      setEnrollments(data);
    } catch {
      setEnrollments([]);
    } finally {
      setLoadingEnrollments(false);
    }
  };

  // Load enrollments when a student is selected
  useEffect(() => {
    if (selectedStudent) {
      fetchEnrollmentsForStudent(selectedStudent);
    }
  }, [selectedStudent]);

  const filteredStudents = students.filter(
    (s) =>
      s.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.studentId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.studentNumber?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.firstName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.lastName?.toLowerCase().includes(searchQuery.toLowerCase())
  );
  console.log(filteredStudents);

  const handleSelectStudent = (student: Student) => {
    setSelectedStudent(student);
    setEnrollments([]);
    setSearchQuery("");
  };

  const validateEnrollment = () => {
    const newErrors = { courseId: "", semester: "", academicYear: "", enrollmentDate: "", credits: "" };
    if (!enrollForm.courseId) newErrors.courseId = "Course is required";
    if (!enrollForm.semester) newErrors.semester = "Semester is required";
    if (!enrollForm.academicYear.trim()) newErrors.academicYear = "Academic year is required";
    if (!enrollForm.enrollmentDate) newErrors.enrollmentDate = "Enrollment date is required";
    if (!enrollForm.credits) newErrors.credits = "Credits are required";
    setErrors(newErrors);
    return Object.values(newErrors).every((e) => !e);
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateEnrollment() || !selectedStudent) return;
    const course = courses.find((c) => c.id === enrollForm.courseId);
    if (!course) return;

    setSaving(true);
    try {
      // POST course/enroll
      await apiPost<{ message: string }>("/api/v1/course/enroll", {
        id: selectedStudent.id,
        courseCode: course.courseId,
        semester: enrollForm.semester,
        academicYear: parseInt(enrollForm.academicYear),
        enrollmentDate: enrollForm.enrollmentDate,
        credits: parseInt(enrollForm.credits)
      });

      // Reload enrollments using the common function
      await fetchEnrollmentsForStudent(selectedStudent);

      setEnrollForm({ courseId: "", semester: "", academicYear: "", enrollmentDate: "", credits: "3" });
      toast.success("Course enrolled successfully");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to enroll";
      toast.error("Enrollment failed", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async () => {

    //onsole.log("selectedEnrollment.id", selectedEnrollment.id);

    if (!selectedEnrollment) return;
    try {

      // DELETE YOUR_API_BASE_URL/enrollments/:id
      await apiDelete(`/api/v1/course/delete-enrollment/${selectedEnrollment.id}`);
      setEnrollments(enrollments.filter((e) => e.id !== selectedEnrollment.id));
      toast.success("Course removed from enrollment");
    } catch {
      toast.error("Failed to remove enrollment");
    } finally {
      setIsRemoveDialogOpen(false);
      setSelectedEnrollment(null);
    }
  };

  const openEditDialog = (enrollment: Enrollment) => {
    setSelectedEnrollment(enrollment);
    setEditForm({
      status: enrollment.status || "ENROLLED",
      grade: enrollment.grade || "N/A",
    });
    setIsEditDialogOpen(true);
  };

  const handleEditSave = async () => {
    if (!editForm.status) return;
    setSaving(true);
    try {
      if (!selectedStudent || !selectedEnrollment) return;
      // PUT update-enrollment

      const payload = {
        id: selectedEnrollment.id,
        status: editForm.status,
        grade: editForm.grade !== "N/A" ? editForm.grade : null
      };

      console.log("=== UPDATE ENROLLMENT DEBUG ===");
      console.log("selectedEnrollment object:", selectedEnrollment);
      console.log("selectedEnrollment.id:", selectedEnrollment.id);
      console.log("typeof id:", typeof selectedEnrollment.id);
      console.log("payload being sent:", JSON.stringify(payload));

      await apiPut(`/api/v1/course/update-enrollment`, payload);
      //onsole.log("selectedEnrollment.id", selectedEnrollment.id);
      setEnrollments(enrollments.map((e) =>
        e.id === selectedEnrollment.id ? { ...e, status: editForm.status, grade: editForm.grade } : e
      ));
      setIsEditDialogOpen(false);
      toast.success("Enrollment updated successfully");
    } catch {
      toast.error("Failed to update enrollment");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Course Enrollment Management</h1>
        <p className="page-description">Enroll students in courses and manage their course registrations.</p>
      </div>

      {!selectedStudent ? (
        /* Student Selection */
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="h-5 w-5" />
              Select a Student
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by Student ID or Name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              {searchQuery && (
                <div className="border rounded-md divide-y">
                  {filteredStudents.map((student) => (
                    <button
                      key={student.id}
                      onClick={() => handleSelectStudent(student)}
                      className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors"
                    >
                      <p className="font-medium">{student.firstName} {student.lastName}</p>
                      <p className="text-sm text-muted-foreground">{student.id || student.studentNumber}</p>
                    </button>
                  ))}
                  {filteredStudents.length === 0 && (
                    <p className="px-4 py-3 text-sm text-muted-foreground">No students found</p>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Selected Student Info */}
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h2 className="font-semibold">{selectedStudent.firstName} {selectedStudent.lastName}</h2>
                    <p className="text-sm text-muted-foreground">
                      {selectedStudent.studentId || selectedStudent.studentNumber}
                    </p>
                  </div>
                </div>
                <Button variant="outline" onClick={() => { setSelectedStudent(null); setEnrollments([]); }}>
                  Change Student
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Enrollment Form */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Plus className="h-5 w-5" />
                  Enroll in Course
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleEnroll} className="space-y-4">
                  <div className="input-wrapper">
                    <Label>Course</Label>
                    <Select value={enrollForm.courseId} onValueChange={(v) => setEnrollForm({ ...enrollForm, courseId: v })} disabled={saving}>
                      <SelectTrigger><SelectValue placeholder="Select course" /></SelectTrigger>
                      <SelectContent>
                        {courses.map((course) => (
                          <SelectItem key={course.id} value={course.id}>
                            {course.courseId} - {course.courseName}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.courseId && <p className="validation-message">{errors.courseId}</p>}
                  </div>
                  <div className="input-wrapper">
                    <Label>Semester</Label>
                    <Select value={enrollForm.semester} onValueChange={(v) => setEnrollForm({ ...enrollForm, semester: v })} disabled={saving}>
                      <SelectTrigger><SelectValue placeholder="Select semester" /></SelectTrigger>
                      <SelectContent>
                        {semesters.map((sem) => (
                          <SelectItem key={sem.value} value={sem.value}>{sem.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.semester && <p className="validation-message">{errors.semester}</p>}
                  </div>
                  <div className="input-wrapper">
                    <Label>Academic Year</Label>
                    <Input
                      placeholder="e.g., 2024/2025"
                      value={enrollForm.academicYear}
                      onChange={(e) => setEnrollForm({ ...enrollForm, academicYear: e.target.value })}
                      disabled={saving}
                    />
                    {errors.academicYear && <p className="validation-message">{errors.academicYear}</p>}
                  </div>
                  <div className="input-wrapper">
                    <Label>Enrollment Date</Label>
                    <Input
                      type="date"
                      value={enrollForm.enrollmentDate}
                      onChange={(e) => setEnrollForm({ ...enrollForm, enrollmentDate: e.target.value })}
                      disabled={saving}
                    />
                    {errors.enrollmentDate && <p className="validation-message">{errors.enrollmentDate}</p>}
                  </div>
                  <div className="input-wrapper">
                    <Label>Credits (For Student-level overriding)</Label>
                    <Input
                      type="number"
                      min="1"
                      max="10"
                      value={enrollForm.credits}
                      onChange={(e) => setEnrollForm({ ...enrollForm, credits: e.target.value })}
                      disabled={saving}
                    />
                    {errors.credits && <p className="validation-message">{errors.credits}</p>}
                  </div>
                  <Button type="submit" className="w-full" disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                    Enroll Course
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Enrolled Courses */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ClipboardList className="h-5 w-5" />
                  Enrolled Courses
                  <Badge variant="secondary" className="ml-auto">{enrollments.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Course</th>
                        <th>Semester</th>
                        <th>Year</th>
                        <th>Enrolled</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {loadingEnrollments ? (
                        <tr>
                          <td colSpan={5} className="text-center py-6 text-muted-foreground">Loading enrollments…</td>
                        </tr>
                      ) : enrollments.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="text-center py-6 text-muted-foreground">No courses enrolled</td>
                        </tr>
                      ) : (
                        enrollments.map((enrollment, index) => (
                          <tr key={enrollment.id || `enrollment-${index}`}>
                            <td>
                              <p className="font-medium">{enrollment.course?.courseCode}</p>
                              <p className="text-xs text-muted-foreground">{enrollment.course?.courseName}</p>
                            </td>
                            <td>{enrollment.semester}</td>
                            <td>{enrollment.academicYear}</td>
                            <td>{new Date(enrollment.enrollmentDate).toLocaleDateString()}</td>
                            <td>
                              <Badge variant="outline">{enrollment.status}</Badge>
                            </td>
                            <td>
                              <Button variant="ghost" size="sm" onClick={() => openEditDialog(enrollment)}>
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                                onClick={() => { setSelectedEnrollment(enrollment); setIsRemoveDialogOpen(true); }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Remove Confirmation */}
      <AlertDialog open={isRemoveDialogOpen} onOpenChange={setIsRemoveDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Course Enrollment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove {selectedEnrollment?.course?.courseName} from {selectedStudent?.firstName} {selectedStudent?.lastName}'s enrollment?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemove} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Edit Enrollment Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Enrollment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="input-wrapper">
              <Label>Course</Label>
              <Input value={selectedEnrollment?.course?.courseName || ""} disabled />
            </div>
            <div className="input-wrapper">
              <Label>Status</Label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm({ ...editForm, status: v })} disabled={saving}>
                <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
                <SelectContent>
                  {statuses.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="input-wrapper">
              <Label>Grade</Label>
              <Select value={editForm.grade} onValueChange={(v) => setEditForm({ ...editForm, grade: v })} disabled={saving}>
                <SelectTrigger><SelectValue placeholder="Select grade" /></SelectTrigger>
                <SelectContent>
                  {grades.map((grade) => (
                    <SelectItem key={grade.value} value={grade.value}>
                      {grade.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)} disabled={saving}>Cancel</Button>
            <Button onClick={handleEditSave} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}