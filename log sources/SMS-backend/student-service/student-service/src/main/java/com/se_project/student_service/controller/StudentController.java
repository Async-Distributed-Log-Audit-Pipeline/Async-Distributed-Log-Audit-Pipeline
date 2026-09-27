package com.se_project.student_service.controller;

import com.se_project.student_service.dto.*;
import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.service.StudentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/student")
public class StudentController {

    @Autowired
    private StudentService studentService;

    @PostMapping(path = "/register-student")
    public ResponseEntity<StudentRegisterResponseDTO> registerStudent(@RequestBody StudentRegisterRequestDTO studentRegisterRequestDTO) {
        StudentRegisterResponseDTO responseDTO = studentService.registerStudent(studentRegisterRequestDTO);
        return ResponseEntity.ok(responseDTO);
    }

    @GetMapping(path = "/get-every-student-details/{studentNumber}")
    public ResponseEntity<StudentDetailsResponseDTO> getAllStudentDetailsByID(@PathVariable String studentNumber) {

        StudentDetailsResponseDTO responseDTO = studentService.getAllStudentDetailsByID(studentNumber);
        return ResponseEntity.ok(responseDTO);
    }

    @GetMapping(path = "/get-all-enrollments/{studentNumber}")
    public ResponseEntity<List<CourseEnrollmentDTO>>  getAllEnrollments(@PathVariable String studentNumber) {

        List<CourseEnrollmentDTO> enrollments = studentService.getAllEnrollments(studentNumber);

        return ResponseEntity.ok(enrollments);
    }

    @GetMapping(path = "/degree-programs")
    public ResponseEntity<List<DegreeProgram>> getAllDegreePrograms() {
        List<DegreeProgram> degreePrograms = studentService.getAllDegreePrograms();
        return ResponseEntity.ok(degreePrograms);
    }

    @GetMapping(path = "/get-all-students")
    public ResponseEntity<List<GetAllStudentsDTO>> getAllStudents(){
        List<GetAllStudentsDTO> responseDTO = studentService.getAllStudentDetails();
        return ResponseEntity.ok(responseDTO);

    }

    @DeleteMapping(path = "/delete-student/{studentNumber}")
    public ResponseEntity<MessageResponseDTO> deleteStudent(@PathVariable String studentNumber) {
        MessageResponseDTO responseDTO = studentService.deleteStudent(studentNumber);
        return ResponseEntity.ok(responseDTO);

    }

    @PutMapping("/update-student-details/{studentNumber}")
    public ResponseEntity<StudentDetailsResponseDTO> updateStudentDetails(
            @PathVariable String studentNumber,
            @RequestBody StudentUpdateRequestDTO dto) {

        StudentDetailsResponseDTO response = studentService.updateStudentDetails(studentNumber, dto);
        return ResponseEntity.ok(response);
    }

    @GetMapping(path = "/count")
    public ResponseEntity<Long> countStudents() {
        long count = studentService.countStudents();
        return ResponseEntity.ok(count);
    }





}
