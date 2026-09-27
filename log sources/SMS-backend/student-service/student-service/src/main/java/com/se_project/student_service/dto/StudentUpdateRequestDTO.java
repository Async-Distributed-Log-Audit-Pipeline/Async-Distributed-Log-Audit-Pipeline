package com.se_project.student_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDate;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class StudentUpdateRequestDTO {
    private String studentIdNumber;
    private String firstName;
    private String lastName;
    private int intake;
    private String address;
    private LocalDate birthday;
    private String degreeProgram;
    private String status;
}