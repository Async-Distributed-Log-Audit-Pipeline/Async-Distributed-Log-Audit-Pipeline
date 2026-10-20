package com.se_project.student_service.service;

import com.se_project.student_service.dto.*;
import com.se_project.student_service.entity.DegreeProgram;

import java.util.List;

public interface StudentService {
    StudentRegisterResponseDTO registerStudent(StudentRegisterRequestDTO studentRegisterRequestDTO);

    StudentDetailsResponseDTO getAllStudentDetailsByID(String studentNumber);

    List<CourseEnrollmentDTO> getAllEnrollments(String studentNumber);

    List<DegreeProgram> getAllDegreePrograms();

    List<GetAllStudentsDTO> getAllStudentDetails();

    MessageResponseDTO deleteStudent(String studentNumber);

    StudentDetailsResponseDTO updateStudentDetails(String studentNumber, StudentUpdateRequestDTO dto);

    long countStudents();
}
