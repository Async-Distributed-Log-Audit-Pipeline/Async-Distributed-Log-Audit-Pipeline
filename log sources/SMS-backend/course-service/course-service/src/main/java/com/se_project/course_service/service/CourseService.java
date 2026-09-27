package com.se_project.course_service.service;

import com.se_project.course_service.dto.*;
import com.se_project.course_service.entity.Course;

import java.util.List;

public interface CourseService {

    CourseCreateResponseDTO createCourse(CourseCreateRequestDTO courseCreateRequestDTO);

    EnrollResponseDTO enrollCourse(EnrollRequestDTO enrollRequestDTO);

    //List<Course> getAllCourses();

    List<CourseEnrollmentDTO> getEnrollmentByStudentNumber(String studentNumber);

    EnrollResponseDTO updateEnrollment( EnrollUpdateDTO enrollUpdateDTO);

    List<GetAllCourseDTO> getAllCourses();

    MessageResponseDTO deleteCourse(Long courseId);

    MessageResponseDTO deleteEnrollment(Long id);

    List<CourseEnrollmentDTO> getCourseHistoryByStudentNumber(String studentNumber);

    CourseResponseDTO updateCourse(Long id, CourseUpdateRequestDTO request);

    long getcount();
}
