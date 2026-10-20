package com.se_project.student_service.repo;

import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.entity.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
@EnableJpaRepositories
public interface StudentRepo extends JpaRepository<Student,Long> {

    @Query("SELECT COUNT(s) FROM Student s WHERE s.degreeProgram = :degreeProgram AND s.intake = :intake")
    long countByDegreeProgramAndIntake(
            @Param("degreeProgram") DegreeProgram degreeProgram,
            @Param("intake") int intake
    );

    boolean existsByStudentIdNumber(String studentIdNumber);

    Student findByStudentNumber(String studentNumber);

    boolean existsByStudentNumber(String studentNumber);

   // List<DegreeProgram> findAllDegreePrograms();
}
