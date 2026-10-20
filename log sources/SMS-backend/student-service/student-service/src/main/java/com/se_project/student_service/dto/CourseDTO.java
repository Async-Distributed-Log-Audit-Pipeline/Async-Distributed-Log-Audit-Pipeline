package com.se_project.student_service.dto;

import jakarta.persistence.NamedEntityGraph;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class CourseDTO {
   // private Long courseId;
    private String courseName;
    private String courseCode;
    private String department;
    private String duration;
    private String description;



}

