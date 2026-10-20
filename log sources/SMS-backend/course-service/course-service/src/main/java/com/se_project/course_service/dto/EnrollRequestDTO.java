package com.se_project.course_service.dto;

import com.se_project.course_service.entity.Course;
import com.se_project.course_service.entity.EnrollmentStatus;
import com.se_project.course_service.entity.Grade;
import com.se_project.course_service.entity.Semester;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class EnrollRequestDTO {

    private String id;  // "STU-2026-0001"
    private String courseCode;  // Reference to Course entity
    private Semester semester;  // SEMESTER_1, SEMESTER_2
    private Integer academicYear;
    private LocalDate enrollmentDate;
    private int credits;
    //private Grade grade;

//    @CreationTimestamp
//    @Column(name = "created_at", nullable = false, updatable = false)
//    private LocalDateTime createdAt;
//
//    @UpdateTimestamp
//    @Column(name = "updated_at")
//    private LocalDateTime updatedAt;
//
//    @Column(name = "enrolled_by", length = 100)
//    private String enrolledBy;  // Admin email who enrolled the student
}
