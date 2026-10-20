package com.se_project.course_service.service.impl;

import com.se_project.course_service.dto.*;
import com.se_project.course_service.entity.Course;
import com.se_project.course_service.entity.CourseEnrollment;
import com.se_project.course_service.entity.EnrollmentStatus;
import com.se_project.course_service.entity.Grade;
import com.se_project.course_service.repo.CourseEnrollmentRepo;
import com.se_project.course_service.repo.CourseRepo;
import com.se_project.course_service.service.CourseService;
import com.se_project.course_service.util.Auditable;
import jakarta.persistence.EntityNotFoundException;
import jakarta.transaction.Transactional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class CourseServiceIMPL implements CourseService {
    @Autowired
    private CourseRepo courseRepo;

    @Autowired
    private CourseEnrollmentRepo courseEnrollmentRepo;


    @Override
    @Transactional
    @Auditable(action = "CREATE_COURSE", entity = "Course")
    public CourseCreateResponseDTO createCourse(CourseCreateRequestDTO courseCreateRequestDTO) {

        Course course = new Course();
        course.setCourseName(courseCreateRequestDTO.getCourseName());
        course.setCourseCode(courseCreateRequestDTO.getCourseCode());
        course.setDepartment(courseCreateRequestDTO.getDepartment());
        course.setDuration(courseCreateRequestDTO.getDuration());
        course.setDescription(courseCreateRequestDTO.getDescription());
        course.setIsActive(true);

        courseRepo.save(course);

        return new CourseCreateResponseDTO("Course created successfully");
    }

    @Override
    @Transactional
    @Auditable(action = "ENROLL_STUDENT", entity = "CourseEnrollment")
    public EnrollResponseDTO enrollCourse(EnrollRequestDTO enrollRequestDTO) {

        CourseEnrollment enrollment = new CourseEnrollment();
        enrollment.setStudentNumber(enrollRequestDTO.getId());
      //  enrollment.setCourse(enrollRequestDTO.getCourse().);

        Course course = courseRepo.findByCourseCode(enrollRequestDTO.getCourseCode());
        enrollment.setCourse(course);
        enrollment.setSemester(enrollRequestDTO.getSemester());
        enrollment.setAcademicYear(enrollRequestDTO.getAcademicYear());
        enrollment.setEnrollmentDate(enrollRequestDTO.getEnrollmentDate());
        enrollment.setStatus(EnrollmentStatus.ENROLLED);
        enrollment.setCredits(enrollRequestDTO.getCredits());

       // courseRepo.save();
        courseEnrollmentRepo.save(enrollment);

        return new EnrollResponseDTO("Course enrolled successfully");
    }



//    @Override
//    public List<CourseEnrollmentDTO> getEnrollmentByStudentNumber(String studentNumber) {
//
//        List<CourseEnrollment> enrollments = courseEnrollmentRepo.findAllByStudentNumber(studentNumber);
//
//        List<CourseEnrollmentDTO> enrollmentDTOs = new ArrayList<>();
//        for(CourseEnrollment enrollment : enrollments){
//            CourseEnrollmentDTO dto = new CourseEnrollmentDTO();
//            dto.setId(enrollment.getId());
//            dto.setStudentNumber(enrollment.getStudentNumber());
//           // dto.setCourseCode(enrollment.getCourse().getCourseCode());
//            //CourseDTO courseDTO = new CourseDTO();
//            CourseDTO courseDTO = new CourseDTO();
//            // courseDTO.setCourseId(enrollment.getCourse().getCourseId());
//            courseDTO.setCourseName(enrollment.getCourse().getCourseName());
//            courseDTO.setCourseCode(enrollment.getCourse().getCourseCode());
//            courseDTO.setDepartment(enrollment.getCourse().getDepartment());
//            courseDTO.setDuration(enrollment.getCourse().getDuration());
//            courseDTO.setDescription(enrollment.getCourse().getDescription());
//            courseDTO.setIsActive(enrollment.getCourse().getIsActive());
//            dto.setCourse(courseDTO);
//
//            dto.setSemester(enrollment.getSemester().name());
//            dto.setAcademicYear(enrollment.getAcademicYear());
//            dto.setEnrollmentDate(enrollment.getEnrollmentDate());
//            dto.setStatus(enrollment.getStatus().name());
//            dto.setGrade(enrollment.getGrade() != null ? enrollment.getGrade().name() : null);
//
//
//
//
////            dto.setSemester(enrollment.getSemester());
////            dto.setAcademicYear(enrollment.getAcademicYear());
////            dto.setEnrollmentDate(enrollment.getEnrollmentDate());
////            dto.setStatus(enrollment.getStatus());
////            dto.setGrade(enrollment.getGrade());
//
//            enrollmentDTOs.add(dto);
//        }
//        if (enrollments.isEmpty()) {
//            throw new RuntimeException("No enrollments found for student number: " + studentNumber);
//        }
//
//
//        return enrollmentDTOs;
//    }

@Override
public List<CourseEnrollmentDTO> getEnrollmentByStudentNumber(String studentNumber) {

    List<CourseEnrollment> enrollments = courseEnrollmentRepo
            .findAllByStudentNumberAndStatus(studentNumber, EnrollmentStatus.ENROLLED);

    if (enrollments.isEmpty()) {
        return new ArrayList<>(); // return empty list instead of throwing
    }

    return mapToDTOList(enrollments);
}

    @Override
    @Transactional
    @Auditable(action = "UPDATE_ENROLLMENT", entity = "CourseEnrollment")
    public EnrollResponseDTO updateEnrollment( EnrollUpdateDTO enrollUpdateDTO) {

        EnrollmentStatus enrollmentStatus = EnrollmentStatus.valueOf(enrollUpdateDTO.getStatus());
        Grade grade = Grade.valueOf(enrollUpdateDTO.getGrade());

      CourseEnrollment enrollment =  courseEnrollmentRepo.findById(enrollUpdateDTO.getId()).orElseThrow(()-> new EntityNotFoundException("User not found"));
       enrollment.setStatus(enrollmentStatus);
       enrollment.setGrade(grade);

         courseEnrollmentRepo.save(enrollment);




        return new EnrollResponseDTO("Enrollment updated successfully");
    }

//    @Override
//    public List<GetAllCourseDTO> getAllCourses() {
//        List<Course> courses= courseRepo.findAll();
//        List<GetAllCourseDTO> courseDTOs = new ArrayList<>();
//        for(Course course : courses){
//            CourseDTO dto = new CourseDTO();
//            dto.setCourseName(course.getCourseName());
//            dto.setCourseCode(course.getCourseCode());
//            dto.setDepartment(course.getDepartment());
//            dto.setDuration(course.getDuration());
//            dto.setDescription(course.getDescription());
//            dto.setIsActive(course.getIsActive());
//            courseDTOs.add(dto);
//
//        }
//
//        return courseDTOs;
//    }

    @Override
    public List<GetAllCourseDTO> getAllCourses() {
        List<Course> courses = courseRepo.findAll();
        List<GetAllCourseDTO> courseDTOs = new ArrayList<>();

        for (Course course : courses) {
            GetAllCourseDTO dto = new GetAllCourseDTO();

            // FIX: id must be sent so edit/delete buttons work
            dto.setId(String.valueOf(course.getCourseId()));

            // FIX: frontend filters/displays by courseId — map from courseCode
            dto.setCourseId(course.getCourseCode());

            dto.setCourseName(course.getCourseName());
            dto.setDescription(course.getDescription());
            dto.setDepartment(course.getDepartment());
            dto.setDuration(course.getDuration());

            // FIX: frontend expects int credits — parse duration or add a credits field
            // If your Course entity has a credits field use that, otherwise default to 3
//            dto.setCredits(course.getCredits() != null ? course.getCredits() : 3);

            // FIX: frontend expects "Active" or "Inactive" string, not boolean
            dto.setStatus(Boolean.TRUE.equals(course.getIsActive()) ? "Active" : "Inactive");

            List<CourseEnrollment> enrollments = courseEnrollmentRepo.findAllByCourse(course);
             dto.setEnrolledStudents(enrollments.size());

            // FIX: frontend shows enrolled count badge — default 0 until you wire course-service
           // dto.setEnrolledStudents(0);

            courseDTOs.add(dto);
        }

        return courseDTOs;
    }

    @Override
    @Transactional
    @Auditable(action = "DELETE_COURSE", entity = "Course")
    public MessageResponseDTO deleteCourse(Long courseId) {
       courseRepo.deleteById(courseId);
         return new MessageResponseDTO("Course deleted successfully");



    }

    @Override
    @Transactional
    @Auditable(action = "DELETE_ENROLLMENT", entity = "CourseEnrollment")
    public MessageResponseDTO deleteEnrollment(Long id) {

        courseEnrollmentRepo.deleteById(id);
        return new MessageResponseDTO("Enrollment deleted successfully");
    }

    @Override
    public List<CourseEnrollmentDTO> getCourseHistoryByStudentNumber(String studentNumber) {
        List<CourseEnrollment> history = courseEnrollmentRepo
                .findAllByStudentNumberAndStatusNot(studentNumber, EnrollmentStatus.ENROLLED);

        if (history.isEmpty()) {
            return new ArrayList<>();
        }

        return mapToDTOList(history);
    }

//    @Override
//    public CourseResponseDTO updateCourse(Long id, CourseUpdateRequestDTO request) {
//        return null;
//    }
@Override
@Transactional
@Auditable(action = "UPDATE_COURSE", entity = "Course")
public CourseResponseDTO updateCourse(Long id, CourseUpdateRequestDTO request) {

    Course course = courseRepo.findById(id)
            .orElseThrow(() -> new RuntimeException("Course not found"));

    // Update fields
    course.setCourseCode(request.getCourseCode());
    course.setCourseName(request.getCourseName());
    course.setDepartment(request.getDepartment());
    course.setDuration(request.getDuration());
    course.setDescription(request.getDescription());

    Course savedCourse = courseRepo.save(course);

    return mapToDTO(savedCourse);
}

    @Override
    public long getcount() {
        return courseEnrollmentRepo.count();
    }

    private CourseResponseDTO mapToDTO(Course course) {

        CourseResponseDTO dto = new CourseResponseDTO();

        dto.setId(course.getCourseId());
        dto.setCourseId(course.getCourseCode());
        dto.setCourseName(course.getCourseName());
        dto.setDepartment(course.getDepartment());
        dto.setDuration(course.getDuration());
        dto.setDescription(course.getDescription());

        dto.setEnrolledStudents(
                course.getEnrollments() != null ? course.getEnrollments().size() : 0
        );

        dto.setStatus(course.getIsActive() ? "Active" : "Inactive");

        return dto;
    }


    private List<CourseEnrollmentDTO> mapToDTOList(List<CourseEnrollment> enrollments) {
        List<CourseEnrollmentDTO> enrollmentDTOs = new ArrayList<>();
        for (CourseEnrollment enrollment : enrollments) {
            CourseEnrollmentDTO dto = new CourseEnrollmentDTO();
            dto.setId(enrollment.getId());
            dto.setStudentNumber(enrollment.getStudentNumber());

            CourseDTO courseDTO = new CourseDTO();
            courseDTO.setCourseName(enrollment.getCourse().getCourseName());
            courseDTO.setCourseCode(enrollment.getCourse().getCourseCode());
            courseDTO.setDepartment(enrollment.getCourse().getDepartment());
            courseDTO.setDuration(enrollment.getCourse().getDuration());
            courseDTO.setDescription(enrollment.getCourse().getDescription());
            courseDTO.setIsActive(enrollment.getCourse().getIsActive());
            dto.setCourse(courseDTO);

            dto.setSemester(enrollment.getSemester().name());
            dto.setAcademicYear(enrollment.getAcademicYear());
            dto.setEnrollmentDate(enrollment.getEnrollmentDate());
            dto.setStatus(enrollment.getStatus().name());
            dto.setGrade(enrollment.getGrade() != null ? enrollment.getGrade().name() : null);

            enrollmentDTOs.add(dto);
        }
        return enrollmentDTOs;
    }
}
