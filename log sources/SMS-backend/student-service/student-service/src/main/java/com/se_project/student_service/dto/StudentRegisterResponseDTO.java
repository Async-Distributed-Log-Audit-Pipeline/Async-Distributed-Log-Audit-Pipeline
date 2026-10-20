package com.se_project.student_service.dto;


import jakarta.persistence.NamedEntityGraph;
import lombok.AllArgsConstructor;
import lombok.Data;

@AllArgsConstructor
@NamedEntityGraph
@Data
public class StudentRegisterResponseDTO {
    private String message;
    private String studentNumber;
}
