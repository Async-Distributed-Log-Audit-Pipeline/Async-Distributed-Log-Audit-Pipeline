package com.se_project.course_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class GetAllCourseDTO {

    private String id;               // frontend: course.id  (used for edit/delete)
    private String courseId;         // frontend: course.courseId  (the display code e.g. CS1012)
    private String courseName;
    private String description;
    private int credits;             // frontend expects number
    private String status;           // frontend expects "Active" or "Inactive"
    private int enrolledStudents;    // frontend badge count — default 0 for now

    private String department;  // <--- ADD THIS
    private String duration;    // <--- ADD THIS
}
