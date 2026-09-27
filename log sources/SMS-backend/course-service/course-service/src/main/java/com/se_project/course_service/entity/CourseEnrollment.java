package com.se_project.course_service.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "course_enrollments")
@AllArgsConstructor
@NamedEntityGraph
@Data
public class CourseEnrollment {

    public CourseEnrollment(){

    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "student_number", nullable = false, length = 20)
    private String studentNumber;  // "STU-2026-0001"

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "course_id", nullable = false)
    private Course course;  // Reference to Course entity

    @Enumerated(EnumType.STRING)
    @Column(name = "semester", nullable = false, length = 20)
    private Semester semester;  // SEMESTER_1, SEMESTER_2

    @Column(name = "academic_year", nullable = false)
    private Integer academicYear;

    @Column(name = "enrollment_date", nullable = false)
    private LocalDate enrollmentDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private EnrollmentStatus status;

    @Enumerated(EnumType.STRING)
    @Column(name = "grade", length = 10)
    private Grade grade;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Column(name = "enrolled_by", length = 100)
    private String enrolledBy;  // Admin email who enrolled the student

//    @Id
//    @GeneratedValue(strategy = GenerationType.IDENTITY)
//    private Long enrollmentId;
//
//    @Column(name = "student_number", nullable = false)
//    private String studentNumber;  // "STU-2026-0001"
//
//    @Column(name = "course_code", nullable = false)
//    private String courseCode;  // "CS101"
//
//    @Column(name = "course_name", nullable = false)
//    private String courseName;
//
//    @Column(name = "semester", nullable = false)
//    private String semester;
//
//    @Column(name = "year", nullable = false)
//    private Integer year;
//
//    @Column(name = "enrollment_date", nullable = false)
//    private LocalDate enrollmentDate;
//
//    @Enumerated(EnumType.STRING)
//    @Column(name = "status", nullable = false)
//    private EnrollmentStatus status = EnrollmentStatus.ENROLLED;
//
    @Column(name = "credits")
    private Integer credits;
//
//    @Column(name = "grade")
//    private String grade;
//
//    @CreationTimestamp
//    @Column(name = "created_at")
//    private LocalDateTime createdAt;
//
//    @UpdateTimestamp
//    @Column(name = "updated_at")
//    private LocalDateTime updatedAt;


}
