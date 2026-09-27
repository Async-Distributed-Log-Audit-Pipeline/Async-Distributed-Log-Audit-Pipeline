import { useState, useEffect } from "react";
import { Plus, Search, Eye, Pencil, Trash2, BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { toast } from "sonner";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";

interface Course {
  id: string; // The database ID (used for edit/delete)
  courseId: string; // "SE", "CS", "IT" (mapped from courseCode in backend)
  courseName: string; // "Software Engineering"
  description: string;
  credits: number;
  status: string; // "Active" | "Inactive"
  enrolledStudents: number;
  // DTO in backend needs to add these for the Edit form to work:
  department?: string;
  duration?: string;
}

const emptyForm = {
  courseCode: "",
  courseName: "",
  department: "",
  duration: "",
  description: "",
};

export default function Courses() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [viewCourse, setViewCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [formData, setFormData] = useState(emptyForm);
  const [errors, setErrors] = useState({
    courseCode: "",
    courseName: "",
    department: "",
    duration: "",
    description: "",
  });

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const data = await apiGet<Course[]>("/api/v1/course/get-all-courses");
      setCourses(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Failed to load courses");
      setCourses([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const filteredCourses = courses.filter(
    (course) =>
      course.courseId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      course.courseName?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenDialog = (course?: Course) => {
    if (course) {
      setSelectedCourse(course);
      setFormData({
        courseCode: course.courseId || "", // Backend sends courseId mapping to courseCode
        courseName: course.courseName || "",
        department: course.department || "", // Will be empty until backend adds to DTO
        duration: course.duration || "",     // Will be empty until backend adds to DTO
        description: course.description || "",
      });
    } else {
      setSelectedCourse(null);
      setFormData(emptyForm);
    }
    setErrors({ courseCode: "", courseName: "", department: "", duration: "", description: "" });
    setIsDialogOpen(true);
  };

  const validateForm = () => {
    const newErrors = { courseCode: "", courseName: "", department: "", duration: "", description: "" };
    if (!formData.courseCode.trim()) newErrors.courseCode = "Course Code is required";
    if (!formData.courseName.trim()) newErrors.courseName = "Course Name is required";
    if (!formData.department.trim()) newErrors.department = "Department is required";
    if (!formData.duration.trim()) newErrors.duration = "Duration is required";
    if (!formData.description.trim()) newErrors.description = "Description is required";

    setErrors(newErrors);
    return Object.values(newErrors).every((e) => !e);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSaving(true);
    try {
      if (selectedCourse) {
        // Assume backend PUT endpoint exists for updating
        await apiPut(`/api/v1/course/update-course/${selectedCourse.id}`, formData);
        toast.success("Course updated successfully");
      } else {
        // MATCHING DTO: CourseCreateRequestDTO
        const payload = {
          courseName: formData.courseName,
          courseCode: formData.courseCode,
          department: formData.department,
          duration: formData.duration,
          description: formData.description,
        };

        const response: any = await apiPost("/api/v1/course/create", payload);
        toast.success("Course added successfully", {
          description: response?.message || "Saved to database",
        });
      }
      setIsDialogOpen(false);
      fetchCourses();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Operation failed";
      toast.error("Failed to save course", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedCourse) return;
    try {
      await apiDelete(`/api/v1/course/delete-course/${selectedCourse.id}`);
      toast.success("Course deleted successfully");
      setCourses(courses.filter((c) => c.id !== selectedCourse.id));
    } catch {
      toast.error("Failed to delete course");
    } finally {
      setIsDeleteDialogOpen(false);
      setSelectedCourse(null);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Course Management</h1>
          <p className="page-description">Add, edit, and manage courses in the system.</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Add Course
        </Button>
      </div>

      {/* Search */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by Course Code or Name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Courses Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Courses ({filteredCourses.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Course Code</th>
                  <th>Course Name</th>
                  <th>Department</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-muted-foreground">
                      Loading courses…
                    </td>
                  </tr>
                ) : filteredCourses.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-muted-foreground">
                      No courses found
                    </td>
                  </tr>
                ) : (
                  filteredCourses.map((course) => (
                    <tr key={course.id}>
                      <td className="font-medium">{course.courseId}</td>
                      <td>{course.courseName}</td>
                      <td>{course.department || "-"}</td>
                      <td className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setViewCourse(course);
                            setIsViewDialogOpen(true);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(course)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setSelectedCourse(course);
                            setIsDeleteDialogOpen(true);
                          }}
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

      {/* Add/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedCourse ? "Edit Course" : "Add New Course"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="form-row">
              <div className="input-wrapper">
                <Label htmlFor="courseCode">Course Code</Label>
                <Input
                  id="courseCode"
                  placeholder="e.g., SE"
                  value={formData.courseCode}
                  onChange={(e) => setFormData({ ...formData, courseCode: e.target.value })}
                  disabled={saving}
                />
                {errors.courseCode && <p className="validation-message">{errors.courseCode}</p>}
              </div>
              <div className="input-wrapper">
                <Label htmlFor="duration">Duration</Label>
                <Input
                  id="duration"
                  placeholder="e.g., 4 Years"
                  value={formData.duration}
                  onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                  disabled={saving}
                />
                {errors.duration && <p className="validation-message">{errors.duration}</p>}
              </div>
            </div>

            <div className="input-wrapper">
              <Label htmlFor="courseName">Course Name</Label>
              <Input
                id="courseName"
                placeholder="e.g., Software Engineering"
                value={formData.courseName}
                onChange={(e) => setFormData({ ...formData, courseName: e.target.value })}
                disabled={saving}
              />
              {errors.courseName && <p className="validation-message">{errors.courseName}</p>}
            </div>

            <div className="input-wrapper">
              <Label htmlFor="department">Department</Label>
              <Input
                id="department"
                placeholder="e.g., Computing"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                disabled={saving}
              />
              {errors.department && <p className="validation-message">{errors.department}</p>}
            </div>

            <div className="input-wrapper">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="Brief course description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={saving}
              />
              {errors.description && <p className="validation-message">{errors.description}</p>}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {selectedCourse ? "Save Changes" : "Add Course"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Course</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{selectedCourse?.courseName}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* View Dialog */}
      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Course Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <p className="text-sm text-muted-foreground">Course Code</p>
              <p className="font-medium">{viewCourse?.courseId}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Course Name</p>
              <p className="font-medium">{viewCourse?.courseName}</p>
            </div>
            <div className="form-row">
              <div>
                <p className="text-sm text-muted-foreground">Department</p>
                <p className="font-medium">{viewCourse?.department || "N/A"}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Duration</p>
                <p className="font-medium">{viewCourse?.duration || "N/A"}</p>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Description</p>
              <p className="font-medium">{viewCourse?.description}</p>
            </div>
            <div className="form-row">

              <div>
                <p className="text-sm text-muted-foreground">Enrolled Students</p>
                <p className="font-medium">{viewCourse?.enrolledStudents ?? 0}</p>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${viewCourse?.status === "Active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                  }`}
              >
                {viewCourse?.status || "Unknown"}
              </span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}