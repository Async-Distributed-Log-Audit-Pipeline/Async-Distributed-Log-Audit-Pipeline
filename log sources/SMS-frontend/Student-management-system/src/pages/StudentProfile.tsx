import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, User, Calendar, MapPin, GraduationCap, BookOpen, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { apiGet } from "@/lib/api";

interface EnrolledCourse {
  courseId: string;
  courseName: string;
  semester: string;
  academicYear: string;
  enrollmentDate: string;
}

interface CourseHistory extends EnrolledCourse {
  status: string;
}

interface StudentDetail {
  id: string;
  studentId: string;
  firstName: string;
  lastName: string;
  address: string;
  dateOfBirth: string;
  degreeProgram: string;
  status: string;
  enrolledCourses: EnrolledCourse[];
  courseHistory: CourseHistory[];
}

export default function StudentProfile() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [studentData, setStudentData] = useState<StudentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // useEffect(() => {
  //   const fetchStudent = async () => {
  //     setLoading(true);
  //     try {
  //       const data = await apiGet<any>(`/api/v1/student/get-every-student-details/${id}`);

  //       console.log("Raw student data:", JSON.stringify(data)); // debug — remove later

  //       const allEnrollments: any[] = data.enrollments ?? [];

  //       setStudentData({
  //         id: data.studentNumber ?? id,
  //         studentId: data.studentIdNumber ?? "",
  //         firstName: data.firstName ?? "",
  //         lastName: data.lastName ?? "",
  //         address: data.address ?? "",
  //         dateOfBirth: data.birthday ?? "",
  //         degreeProgram: data.degreeProgram != null
  //           ? String(data.degreeProgram).replace(/_/g, " ")
  //           : "",

  //         // ✅ FIX: course data is nested inside e.course object
  //         // ✅ FIX: status filter changed from "ACTIVE" → "ENROLLED"
  //         enrolledCourses: allEnrollments
  //           .filter((e) => !e.status || e.status === "ENROLLED")
  //           .map((e) => ({
  //             courseId: e.course?.courseCode ?? e.courseId ?? e.courseCode ?? "",
  //             courseName: e.course?.courseName ?? e.courseName ?? "",
  //             semester: e.semester ?? "",
  //             academicYear: String(e.academicYear ?? ""),
  //             enrollmentDate: e.enrollmentDate ?? "",
  //           })),

  //         courseHistory: allEnrollments
  //           .filter((e) => e.status && e.status !== "ENROLLED")
  //           .map((e) => ({
  //             courseId: e.course?.courseCode ?? e.courseId ?? e.courseCode ?? "",
  //             courseName: e.course?.courseName ?? e.courseName ?? "",
  //             semester: e.semester ?? "",
  //             academicYear: String(e.academicYear ?? ""),
  //             enrollmentDate: e.enrollmentDate ?? "",
  //             status: e.status ?? "Completed",
  //           })),
  //       });

  //     } catch {
  //       // Student not found or API not connected — leave studentData null
  //     } finally {
  //       setLoading(false);
  //     }
  //   };
  //   if (id) fetchStudent();
  // }, [id]);
  useEffect(() => {
    const fetchStudent = async () => {
      setLoading(true);
      try {
        // Fetch student details and course history in parallel
        const [data, historyData] = await Promise.all([
          apiGet<any>(`/api/v1/student/get-every-student-details/${id}`),
          apiGet<any[]>(`/api/v1/course/getCourseHistoryByStudentNumber/${id}`).catch(() => []),
        ]);

        const allEnrollments: any[] = data.enrollments ?? [];

        setStudentData({
          id: data.studentNumber ?? id,
          studentId: data.studentNumber ?? "",
          firstName: data.firstName ?? "",
          lastName: data.lastName ?? "",
          address: data.address ?? "",
          dateOfBirth: data.birthday ?? "",
          degreeProgram: data.degreeProgram != null
            ? String(data.degreeProgram).replace(/_/g, " ")
            : "",
          status: data.status ?? "ACTIVE",

          // Current enrollments — from student-service (already filtered to ENROLLED only)
          enrolledCourses: allEnrollments.map((e) => ({
            courseId: e.course?.courseCode ?? e.courseId ?? e.courseCode ?? "",
            courseName: e.course?.courseName ?? e.courseName ?? "",
            semester: e.semester ?? "",
            academicYear: String(e.academicYear ?? ""),
            enrollmentDate: e.enrollmentDate ?? "",
          })),

          // Course history — from the new dedicated course-service endpoint
          courseHistory: historyData.map((e: any) => ({
            courseId: e.course?.courseCode ?? "",
            courseName: e.course?.courseName ?? "",
            semester: e.semester ?? "",
            academicYear: String(e.academicYear ?? ""),
            enrollmentDate: e.enrollmentDate ?? "",
            status: e.status ?? "Completed",
          })),
        });

      } catch {
        // Student not found or API not connected — leave studentData null
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchStudent();
  }, [id]);

  if (loading) {
    return (
      <div className="page-container">
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          Loading student profile…
        </div>
      </div>
    );
  }

  if (!studentData) {
    return (
      <div className="page-container">
        <Button variant="ghost" onClick={() => navigate("/students")} className="mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Students
        </Button>
        <p className="text-muted-foreground">Student not found.</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Back Button */}
      <Button variant="ghost" onClick={() => navigate("/students")} className="mb-4">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Students
      </Button>

      <div className="page-header flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">{studentData.firstName} {studentData.lastName}</h1>
            <Badge
              variant="outline"
              className={`
                ${studentData.status === 'ACTIVE' ? 'bg-success/10 text-success border-success/20' : ''}
                ${studentData.status === 'INACTIVE' ? 'bg-destructive/10 text-destructive border-destructive/20' : ''}
                ${studentData.status === 'GRADUATED' ? 'bg-primary/10 text-primary border-primary/20' : ''}
                ${['WITHDRAWN', 'SUSPENDED', 'TRANSFERRED'].includes(studentData.status) ? 'bg-warning/10 text-warning border-warning/20' : ''}
                font-medium capitalize
              `}
            >
              {studentData.status.toLowerCase()}
            </Badge>
          </div>
          <p className="page-description">{studentData.studentId}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate(`/students/${id}/edit`)}>
            Edit Profile
          </Button>
          <Button onClick={() => navigate(`/enrollment?student=${id}`)}>
            <ClipboardList className="h-4 w-4 mr-2" />
            Manage Courses
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Personal Information */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <User className="h-5 w-5" />
              Personal Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3">
              <GraduationCap className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">Degree Program</p>
                <p className="text-sm font-medium">{studentData.degreeProgram}</p>
              </div>
            </div>
            <Separator />
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">Date of Birth</p>
                <p className="text-sm font-medium">
                  {new Date(studentData.dateOfBirth).toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'long', year: 'numeric',
                  })}
                </p>
              </div>
            </div>
            <Separator />
            <div className="flex items-start gap-3">
              <MapPin className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">Address</p>
                <p className="text-sm font-medium">{studentData.address}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Enrolled Courses */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Current Enrolled Courses
              <Badge variant="secondary" className="ml-auto">
                {studentData.enrolledCourses.length} courses
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Course ID</th>
                    <th>Course Name</th>
                    <th>Semester</th>
                    <th>Academic Year</th>
                    <th>Enrolled</th>
                  </tr>
                </thead>
                <tbody>
                  {studentData.enrolledCourses.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-6 text-muted-foreground">
                        No current enrollments
                      </td>
                    </tr>
                  ) : (
                    studentData.enrolledCourses.map((course, index) => (
                      <tr key={course.courseId || `enrolled-${index}`}>
                        <td className="font-medium">{course.courseId}</td>
                        <td>{course.courseName}</td>
                        <td>{course.semester}</td>
                        <td>{course.academicYear}</td>
                        <td>{new Date(course.enrollmentDate).toLocaleDateString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Course History */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Course History
              <Badge variant="outline" className="ml-auto">
                {studentData.courseHistory.length} past courses
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Course ID</th>
                    <th>Course Name</th>
                    <th>Semester</th>
                    <th>Academic Year</th>
                    <th>Enrolled</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {studentData.courseHistory.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-6 text-muted-foreground">
                        No course history
                      </td>
                    </tr>
                  ) : (
                    studentData.courseHistory.map((course, index) => (
                      <tr key={course.courseId || `history-${index}`}>
                        <td className="font-medium">{course.courseId}</td>
                        <td>{course.courseName}</td>
                        <td>{course.semester}</td>
                        <td>{course.academicYear}</td>
                        <td>{new Date(course.enrollmentDate).toLocaleDateString()}</td>
                        <td>
                          <Badge variant="secondary" className="bg-success/10 text-success border-0">
                            {course.status ?? "Completed"}
                          </Badge>
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
  );
}