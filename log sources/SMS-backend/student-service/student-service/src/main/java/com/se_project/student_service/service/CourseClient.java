package com.se_project.student_service.service;

import com.se_project.student_service.dto.CourseEnrollmentDTO;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.util.List;

@FeignClient("course-service")
public interface CourseClient {

    @GetMapping("/api/v1/course/getEnrollmentByStudentNumber/{studentNumber}")
    List<CourseEnrollmentDTO> getEnrollmentsByStudentNumber(@PathVariable("studentNumber") String studentNumber);


}
