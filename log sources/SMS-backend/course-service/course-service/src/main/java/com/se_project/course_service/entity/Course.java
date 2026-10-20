package com.se_project.course_service.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "courses")
@AllArgsConstructor

@Data
public class Course {

    public Course(){

    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long courseId;

    @Column(name = "course_name", nullable = false)
    private String courseName;  // "Software Engineering"


    // This is what Student Service stores
    @Column(name = "course_code", unique = true, nullable = false)
    private String courseCode;  // "SE", "CS", "IT"

    @Column(name = "department")
    private String department;

    @Column(name = "duration", nullable = false)
    private String duration;

    @Column(name = "description")
    private String description;

    @Column(name = "is_active", nullable = false)
    private Boolean isActive;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    // ✅ One course can have many enrollments
    @OneToMany(mappedBy = "course", cascade = CascadeType.ALL)
    private List<CourseEnrollment> enrollments;

}
