package com.se_project.student_service.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "students")
@AllArgsConstructor
@NamedEntityGraph
@Data
public class Student {

    public Student(){

    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long stuId;

    @Column(name = "student_number", unique = true, nullable = false)
    private String studentNumber;

    @Column(name = "first_name", nullable = false)
    private String firstName;

    @Column(name = "last_name", nullable = false)
    private String lastName;

    @Column(name = "intake", nullable = false)
    private int intake;

    @Column(name = "address", nullable = false)
    private String address;

    @Column(name = "birthday", nullable = false)
    private LocalDate birthday;

    @Column(name = "student_id_number", unique = true, nullable = false)
    private String studentIdNumber;

    // ✅ SIMPLIFIED: Degree program as ENUM (no separate table)
    @Enumerated(EnumType.STRING)
    @Column(name = "degree_program", nullable = false, length = 50)
    private DegreeProgram degreeProgram;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private StudentStatus status;

    //FOr the audit things
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Column(name = "created_by")
    private String createdBy;

    @Column(name = "updated_by")
    private String updatedBy;


}
