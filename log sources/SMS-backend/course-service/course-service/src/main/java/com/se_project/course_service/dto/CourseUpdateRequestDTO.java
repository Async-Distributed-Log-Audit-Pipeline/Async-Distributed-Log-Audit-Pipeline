package com.se_project.course_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class CourseUpdateRequestDTO {

    private String courseCode;
    private String courseName;
    private String department;
    private String duration;
    private String description;
}
