package com.se_project.course_service.dto;


import jakarta.persistence.NamedEntityGraph;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class EnrollUpdateDTO {

    private Long id;
    private String status;
    private String grade;
}
