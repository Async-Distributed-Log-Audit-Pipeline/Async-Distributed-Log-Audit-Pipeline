package com.se_project.course_service.dto;


import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class CourseEnrollmentDTO {
    private Long id;
    private String studentNumber;
    private CourseDTO course;
    private String semester;
    private Integer academicYear;
    private LocalDate enrollmentDate;
    private String status;
    private String grade;
//    private LocalDateTime createdAt;
//    private LocalDateTime updatedAt;
//    private String enrolledBy;
}
