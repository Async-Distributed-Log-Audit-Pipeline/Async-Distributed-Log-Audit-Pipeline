package com.se_project.course_service.controller;

import com.se_project.course_service.dto.*;
import com.se_project.course_service.entity.Course;
import com.se_project.course_service.service.CourseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/course")
public class CourseController {

    @Autowired
    private CourseService courseService;


    @PostMapping(path = "/create")
    public ResponseEntity<CourseCreateResponseDTO> createCourse(@RequestBody CourseCreateRequestDTO courseCreateRequestDTO) {
        CourseCreateResponseDTO responseDTO = courseService.createCourse(courseCreateRequestDTO);
        return ResponseEntity.ok(responseDTO);
    }

    @PostMapping(path = "/enroll")
    public ResponseEntity<EnrollResponseDTO> enrollCourse(@RequestBody EnrollRequestDTO enrollRequestDTO) {

        System.out.println("Received enrollment request: " + enrollRequestDTO);
        EnrollResponseDTO responseDTO = courseService.enrollCourse(enrollRequestDTO);
        return ResponseEntity.ok(responseDTO);
    }

    @GetMapping( path = "/get-all-courses")
    public ResponseEntity<List<GetAllCourseDTO>> getAllCourses() {
        List<GetAllCourseDTO> courses = courseService.getAllCourses();
        return ResponseEntity.ok(courses);
    }

    @GetMapping("/getEnrollmentByStudentNumber/{studentNumber}")
    public ResponseEntity<List<CourseEnrollmentDTO>> getEnrollmentByStudentNumber(@PathVariable String studentNumber) {
        List<CourseEnrollmentDTO> enrollments = courseService.getEnrollmentByStudentNumber(studentNumber);
        return ResponseEntity.ok(enrollments);
    }

    @PutMapping(path = "/update-enrollment")
    public ResponseEntity<EnrollResponseDTO> updateEnrollment( @RequestBody EnrollUpdateDTO enrollUpdateDTO) {

        EnrollResponseDTO reponse = courseService.updateEnrollment(enrollUpdateDTO);
        return ResponseEntity.ok(reponse) ;
    }

    @DeleteMapping(path = "/delete-course/{courseId}")
    public ResponseEntity<MessageResponseDTO> deleteCourse(@PathVariable Long courseId) {
        MessageResponseDTO responseDTO = courseService.deleteCourse(courseId);
        return ResponseEntity.ok(responseDTO);
    }

    @DeleteMapping(path = "/delete-enrollment/{id}")
    public ResponseEntity<MessageResponseDTO> deleteEnrollment(@PathVariable Long id) {
        MessageResponseDTO responseDTO = courseService.deleteEnrollment(id);
        return ResponseEntity.ok(responseDTO);
    }

    @GetMapping("/getCourseHistoryByStudentNumber/{studentNumber}")
    public ResponseEntity<List<CourseEnrollmentDTO>> getCourseHistoryByStudentNumber(
            @PathVariable String studentNumber) {
        List<CourseEnrollmentDTO> history = courseService.getCourseHistoryByStudentNumber(studentNumber);

        System.out.println("Course history for student number " + studentNumber + ": " + history);
        return ResponseEntity.ok(history);
    }

    @PutMapping("/update-course/{id}")
    public ResponseEntity<CourseResponseDTO> updateCourse(
            @PathVariable Long id,
            @RequestBody CourseUpdateRequestDTO request
    ) {

        CourseResponseDTO response = courseService.updateCourse(id, request);

        return ResponseEntity.ok(response);
    }

    @GetMapping(path = "/count")
    public ResponseEntity<Long> countCourses() {
        long count = courseService.getAllCourses().size();
        return ResponseEntity.ok(count);
    }

    @GetMapping(path = "/enrollment-count")
    public ResponseEntity<Long> countEnrollments() {
        long count = courseService.getcount();
        return ResponseEntity.ok(count);
    }






}
