package com.se_project.student_service.dto;


import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.entity.StudentStatus;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@AllArgsConstructor
@NamedEntityGraph
@Data
public class StudentRegisterRequestDTO {


    private String firstName;
    private String lastName;
    private int intake;
    private String address;
    private LocalDate birthday;
    private String studentIdNumber;
    private DegreeProgram degreeProgram;



}
