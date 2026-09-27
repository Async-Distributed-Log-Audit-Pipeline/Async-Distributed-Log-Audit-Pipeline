package com.se_project.student_service.service.IMPL;

import com.se_project.student_service.dto.*;
import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.entity.Student;
import com.se_project.student_service.entity.StudentStatus;
import com.se_project.student_service.repo.StudentRepo;
import com.se_project.student_service.service.CourseClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class StudentServiceIMPLTest {

    @Mock
    private StudentRepo studentRepo;

    @Mock
    private CourseClient courseClient;

    @InjectMocks
    private StudentServiceIMPL studentService;

    private Student student;
    private StudentRegisterRequestDTO registerRequest;

    @BeforeEach
    void setUp() {
        student = new Student();
        student.setStudentNumber("SE-2023-1");
        student.setFirstName("Alice");
        student.setLastName("Smith");
        student.setStudentIdNumber("123456789V");
        student.setDegreeProgram(DegreeProgram.SOFTWARE_ENGINEERING);
        student.setIntake(2023);
        student.setStatus(StudentStatus.ACTIVE);

        registerRequest = new StudentRegisterRequestDTO(
                "Alice",
                "Smith",
                2023,
                "123 Main St",
                LocalDate.of(2000, 1, 1),
                "123456789V",
                DegreeProgram.SOFTWARE_ENGINEERING
        );
    }

    @Test
    void registerStudent_Success() {
        when(studentRepo.existsByStudentIdNumber(anyString())).thenReturn(false);
        when(studentRepo.countByDegreeProgramAndIntake(any(DegreeProgram.class), anyInt())).thenReturn(0L);
        when(studentRepo.save(any(Student.class))).thenReturn(student);

        StudentRegisterResponseDTO response = studentService.registerStudent(registerRequest);

        assertNotNull(response);
        assertEquals("Student registered successfully", response.getMessage());
        assertEquals("SE-2023-1", response.getStudentNumber());
        verify(studentRepo, times(1)).save(any(Student.class));
    }

    @Test
    void registerStudent_ThrowsException_WhenStudentExists() {
        when(studentRepo.existsByStudentIdNumber(anyString())).thenReturn(true);

        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            studentService.registerStudent(registerRequest);
        });

        assertTrue(exception.getMessage().contains("already exists"));
        verify(studentRepo, never()).save(any(Student.class));
    }

    @Test
    void getAllStudentDetailsByID_Success() {
        when(studentRepo.findByStudentNumber("SE-2023-1")).thenReturn(student);
        when(courseClient.getEnrollmentsByStudentNumber("SE-2023-1")).thenReturn(new ArrayList<>());

        StudentDetailsResponseDTO response = studentService.getAllStudentDetailsByID("SE-2023-1");

        assertNotNull(response);
        assertEquals("Alice", response.getFirstName());
        assertEquals("SE-2023-1", response.getStudentNumber());
    }

    @Test
    void getAllStudentDetailsByID_ThrowsException_WhenNotFound() {
        when(studentRepo.findByStudentNumber("UNKNOWN")).thenReturn(null);

        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            studentService.getAllStudentDetailsByID("UNKNOWN");
        });

        assertTrue(exception.getMessage().contains("not found"));
    }

    @Test
    void deleteStudent_Success() {
        when(studentRepo.findByStudentNumber("SE-2023-1")).thenReturn(student);

        MessageResponseDTO response = studentService.deleteStudent("SE-2023-1");

        assertNotNull(response);
        assertTrue(response.getMessage().contains("deleted successfully"));
        verify(studentRepo, times(1)).delete(student);
    }
}
