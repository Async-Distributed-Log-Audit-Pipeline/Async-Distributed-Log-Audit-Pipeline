package com.se_project.student_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class GetAllStudentsDTO {

    // Matches frontend: student.id  (used for navigate/delete — should be studentNumber)
    private String id;

    // Matches frontend: student.studentId  (the NIC / display ID)
    private String studentId;
    private String studentNumber;

    private String firstName;
    private String lastName;

    // Frontend filters/displays this as plain text — send enum name as String
    private String degreeProgram;

    // Matches frontend: student.enrolledCourses  (badge count)
    private int enrolledCourses;
}