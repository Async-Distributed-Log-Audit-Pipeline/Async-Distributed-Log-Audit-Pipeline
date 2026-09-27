package com.se_project.course_service.repo;

import com.se_project.course_service.dto.CourseEnrollmentDTO;
import com.se_project.course_service.entity.Course;
import com.se_project.course_service.entity.CourseEnrollment;
import com.se_project.course_service.entity.EnrollmentStatus;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
@EnableJpaRepositories
public interface CourseEnrollmentRepo extends CrudRepository<CourseEnrollment, Long> {
    List<CourseEnrollment> findAllByStudentNumber(String studentNumber);

    boolean existsByStudentNumber(String studentNumber);

    List<CourseEnrollment> findAllByCourse(Course course);

   // List<CourseEnrollment> findAllByStudentNumber(String studentNumber);
    List<CourseEnrollment> findAllByStudentNumberAndStatus(String studentNumber, EnrollmentStatus status);
    List<CourseEnrollment> findAllByStudentNumberAndStatusNot(String studentNumber, EnrollmentStatus status);
}
