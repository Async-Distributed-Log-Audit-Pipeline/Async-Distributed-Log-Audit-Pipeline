package com.se_project.student_service.dto;

import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.entity.StudentStatus;
import jakarta.persistence.Column;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.NamedEntityGraph;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDate;
import java.util.List;

@AllArgsConstructor
@NamedEntityGraph
@Data
public class StudentDetailsResponseDTO {
    private String firstName;
    private String lastName;
    private String studentNumber;
    private int intake;
    private String address;
    private LocalDate birthday;
    private String studentIdNumber;
    private DegreeProgram degreeProgram;
    private StudentStatus status;
    private List<CourseEnrollmentDTO> enrollments;

    public StudentDetailsResponseDTO() {

    }



}
