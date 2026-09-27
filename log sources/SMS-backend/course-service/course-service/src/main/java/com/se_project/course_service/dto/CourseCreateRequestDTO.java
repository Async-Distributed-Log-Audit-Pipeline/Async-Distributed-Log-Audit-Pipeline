package com.se_project.course_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class CourseCreateRequestDTO {

    private String courseName;  // "Software Engineering"
    private String courseCode;  // "SE", "CS", "IT"
    private String department;
    private String duration;
    private String description;




}