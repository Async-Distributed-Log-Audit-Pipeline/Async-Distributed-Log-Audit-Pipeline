package com.se_project.course_service.service.impl;

import com.se_project.course_service.dto.*;
import com.se_project.course_service.entity.*;
import com.se_project.course_service.repo.CourseEnrollmentRepo;
import com.se_project.course_service.repo.CourseRepo;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class CourseServiceIMPLTest {

    @Mock
    private CourseRepo courseRepo;

    @Mock
    private CourseEnrollmentRepo courseEnrollmentRepo;

    @InjectMocks
    private CourseServiceIMPL courseService;

    private Course course;
    private CourseCreateRequestDTO createRequest;
    private EnrollRequestDTO enrollRequest;
    private CourseEnrollment enrollment;

    @BeforeEach
    void setUp() {
        course = new Course();
        course.setCourseId(1L);
        course.setCourseCode("CS101");
        course.setCourseName("Introduction to CS");
        course.setIsActive(true);

        createRequest = new CourseCreateRequestDTO();
        createRequest.setCourseCode("CS101");
        createRequest.setCourseName("Introduction to CS");
        createRequest.setDepartment("Computer Science");
        createRequest.setDuration("4 Months");
        createRequest.setDescription("Basic CS course");

        enrollRequest = new EnrollRequestDTO();
        enrollRequest.setId("SE-2023-1");
        enrollRequest.setCourseCode("CS101");
        enrollRequest.setSemester(Semester.SEMESTER_1);
        enrollRequest.setAcademicYear(2023);
        enrollRequest.setEnrollmentDate(LocalDate.now());
        enrollRequest.setCredits(3);

        enrollment = new CourseEnrollment();
        enrollment.setId(1L);
        enrollment.setStudentNumber("SE-2023-1");
        enrollment.setCourse(course);
        enrollment.setStatus(EnrollmentStatus.ENROLLED);
    }

    @Test
    void createCourse_Success() {
        when(courseRepo.save(any(Course.class))).thenReturn(course);

        CourseCreateResponseDTO response = courseService.createCourse(createRequest);

        assertNotNull(response);
        assertEquals("Course created successfully", response.getMessage());
        verify(courseRepo, times(1)).save(any(Course.class));
    }

    @Test
    void enrollCourse_Success() {
        when(courseRepo.findByCourseCode("CS101")).thenReturn(course);
        when(courseEnrollmentRepo.save(any(CourseEnrollment.class))).thenReturn(enrollment);

        EnrollResponseDTO response = courseService.enrollCourse(enrollRequest);

        assertNotNull(response);
        assertEquals("Course enrolled successfully", response.getMessage());
        verify(courseEnrollmentRepo, times(1)).save(any(CourseEnrollment.class));
    }

    @Test
    void updateEnrollment_Success() {
        EnrollUpdateDTO updateDTO = new EnrollUpdateDTO();
        updateDTO.setId(1L);
        updateDTO.setStatus("COMPLETED");
        updateDTO.setGrade("A");

        when(courseEnrollmentRepo.findById(1L)).thenReturn(Optional.of(enrollment));
        when(courseEnrollmentRepo.save(any(CourseEnrollment.class))).thenReturn(enrollment);

        EnrollResponseDTO response = courseService.updateEnrollment(updateDTO);

        assertNotNull(response);
        assertEquals("Enrollment updated successfully", response.getMessage());
        assertEquals(EnrollmentStatus.COMPLETED, enrollment.getStatus());
        assertEquals(Grade.A, enrollment.getGrade());
    }

    @Test
    void deleteCourse_Success() {
        MessageResponseDTO response = courseService.deleteCourse(1L);

        assertNotNull(response);
        assertTrue(response.getMessage().contains("deleted successfully"));
        verify(courseRepo, times(1)).deleteById(1L);
    }
}
