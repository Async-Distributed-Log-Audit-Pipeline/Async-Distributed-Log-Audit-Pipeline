package com.se_project.student_service.dto;

import jakarta.persistence.NamedEntityGraph;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@AllArgsConstructor
@NamedEntityGraph
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
