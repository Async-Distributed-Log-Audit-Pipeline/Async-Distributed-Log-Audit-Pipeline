package com.se_project.course_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class CourseResponseDTO {

    private Long id;
    private String courseId; // mapped from courseCode
    private String courseName;
    private String department;
    private String duration;
    private String description;
    private int enrolledStudents;
    private String status;

}
