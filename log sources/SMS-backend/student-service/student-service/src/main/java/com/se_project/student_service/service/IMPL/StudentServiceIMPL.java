package com.se_project.student_service.service.IMPL;

import com.se_project.student_service.dto.*;
import com.se_project.student_service.entity.DegreeProgram;
import com.se_project.student_service.entity.Student;
import com.se_project.student_service.entity.StudentStatus;
import com.se_project.student_service.repo.StudentRepo;
import com.se_project.student_service.service.CourseClient;
import com.se_project.student_service.service.StudentService;
import com.se_project.student_service.util.Auditable;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class StudentServiceIMPL implements StudentService {

    @Autowired
    private StudentRepo studentRepo;

    @Autowired
    private CourseClient courseClient;

    @Transactional
    @Auditable(action = "GENERATE_STUDENT_NUMBER", entity = "Student")
    public String generateStudentNumber(DegreeProgram degreeProgram, int intake) {

        // Get degree code from enum (SE, CS, IT, etc.)
        String degreeCode = degreeProgram.getCode();

        // Count existing students with same degree program and intake
        long count = studentRepo.countByDegreeProgramAndIntake(degreeProgram, intake);

        // Generate sequential number (starts from 1)
        long sequentialNumber = count + 1;

        // Format: DegreeCode-Intake-Number
        String studentNumber = String.format("%s-%d-%d", degreeCode, intake, sequentialNumber);

      //  log.info("Generated student number: {}", studentNumber);

        return studentNumber;
    }



    @Override
    @Transactional
    @Auditable(action = "CREATE_STUDENT", entity = "Student")
    public StudentRegisterResponseDTO registerStudent(StudentRegisterRequestDTO requestDTO) {

       // student.setStudentNumber(generateStudentNumber(studentRegisterRequestDTO.getDegreeProgram().getCode()));

        if (studentRepo.existsByStudentIdNumber(requestDTO.getStudentIdNumber())) {
            throw new RuntimeException(
                    "Student with ID number " + requestDTO.getStudentIdNumber() + " already exists"
            );
        }

        Student student = new Student();

        // Generate unique student number
        String studentNumber = generateStudentNumber(
                requestDTO.getDegreeProgram(),
                requestDTO.getIntake()
        );
        student.setStudentNumber(studentNumber);

        // Set personal details
        student.setFirstName(requestDTO.getFirstName());
        student.setLastName(requestDTO.getLastName());
        student.setAddress(requestDTO.getAddress());
        student.setBirthday(requestDTO.getBirthday());
        student.setStudentIdNumber(requestDTO.getStudentIdNumber());

        // Set degree program and intake
        student.setDegreeProgram(requestDTO.getDegreeProgram());
        student.setIntake(requestDTO.getIntake());

        // Set status as ACTIVE by default
        student.setStatus(StudentStatus.ACTIVE);

        // Save to database
        Student savedStudent = studentRepo.save(student);



        return new StudentRegisterResponseDTO("Student registered successfully", savedStudent.getStudentNumber());
    }

    //Get requests walata @Auditable eka danna one na mokada ehem unoth admin refresh karana hama prama log wadinna gannawa
    @Override
    public StudentDetailsResponseDTO getAllStudentDetailsByID(String studentNumber) {
        Student student = studentRepo.findByStudentNumber(studentNumber);
        if (student == null) {
            throw  new RuntimeException("Student with number " + studentNumber + " not found");
        }else {

            StudentDetailsResponseDTO responseDTO = new StudentDetailsResponseDTO();
            responseDTO.setFirstName(student.getFirstName());
            responseDTO.setLastName(student.getLastName());
            responseDTO.setStudentNumber(student.getStudentNumber());
            responseDTO.setIntake(student.getIntake());

            responseDTO.setAddress(student.getAddress());
            responseDTO.setBirthday(student.getBirthday());
            responseDTO.setStudentIdNumber(student.getStudentIdNumber());
            responseDTO.setDegreeProgram(student.getDegreeProgram());
            responseDTO.setStatus(student.getStatus());

            List<CourseEnrollmentDTO> enrollments = new ArrayList<>();

            try{
                enrollments = courseClient.getEnrollmentsByStudentNumber(studentNumber);
                //responseDTO.setCourseEnrollments(enrollments);
                responseDTO.setEnrollments(enrollments);
            }catch (Exception e){
                // Log the exception (you can use a logging framework here)
                System.err.println("Error fetching course enrollments: " + e.getMessage());
            }


            return responseDTO;

        }

    }

    @Override
    public List<CourseEnrollmentDTO> getAllEnrollments(String studentNumber) {

        if (!studentRepo.existsByStudentNumber(studentNumber)) {
            throw  new RuntimeException("Student with number " + studentNumber + " not found");

        }

        List<CourseEnrollmentDTO> enrollments = courseClient.getEnrollmentsByStudentNumber(studentNumber);

        return enrollments;
    }

    @Override
    public List<DegreeProgram> getAllDegreePrograms() {
        List<DegreeProgram> degreePrograms = new ArrayList<>();
        degreePrograms.addAll(List.of(DegreeProgram.values()));


        return degreePrograms;
    }

    @Override
    public List<GetAllStudentsDTO> getAllStudentDetails() {
            List<Student> students = studentRepo.findAll();

       // List<CourseEnrollmentDTO> enrollments = courseClient.getEnrollmentsByStudentNumber(studentNumber);


        List<GetAllStudentsDTO> studentDetailsList = new ArrayList<>();

            for (Student student : students) {
                GetAllStudentsDTO dto = new GetAllStudentsDTO();
                dto.setId(student.getStudentNumber());          // used in navigate(`/students/${student.id}`)
                dto.setStudentId(student.getStudentIdNumber()); // the NIC shown in the table
                dto.setFirstName(student.getFirstName());
                dto.setLastName(student.getLastName());
                dto.setDegreeProgram(student.getDegreeProgram().name()); // enum → "SOFTWARE_ENGINEERING"
                dto.setStudentNumber(student.getStudentNumber());


//                List<CourseEnrollmentDTO> enrollments = courseClient.getEnrollmentsByStudentNumber(student.getStudentNumber());
//                System.out.println("Enrollments for student " + student.getStudentNumber() + ": " + enrollments);
//                int enrollmentCount = enrollments.size();
//                dto.setEnrolledCourses(enrollmentCount);

                // ✅ Feign call wrapped — course-service failure must NOT crash student-service
                try {
                    List<CourseEnrollmentDTO> enrollments =
                            courseClient.getEnrollmentsByStudentNumber(student.getStudentNumber());
                    int enrollmentCount = enrollments.size();
                    dto.setEnrolledCourses(enrollmentCount);
                } catch (Exception e) {
                    // course-service is down or erroring — return student data with empty enrollments
                    System.err.println("Could not fetch enrollments for " + student.getStudentNumber() + ": " + e.getMessage());
                   // responseDTO.setEnrollments(Collections.emptyList());
                }



                studentDetailsList.add(dto);
            }

            // You can return the list of student details as needed
            // For example, you could wrap it in another DTO or return it directly
        return studentDetailsList;
    }

    @Override
    @Transactional
    @Auditable(action = "DELETE_STUDENT", entity = "Student")
    public MessageResponseDTO deleteStudent(String studentNumber) {
        Student student = studentRepo.findByStudentNumber(studentNumber);
        if (student == null) {
            throw  new RuntimeException("Student with number " + studentNumber + " not found");
        }
        studentRepo.delete(student);
        return new MessageResponseDTO("Student with number " + studentNumber + " deleted successfully");
        //return null;
    }

    @Override
    @Transactional
    @Auditable(action = "UPDATE_STUDENT", entity = "Student")
    public StudentDetailsResponseDTO updateStudentDetails(String studentNumber, StudentUpdateRequestDTO dto) {
        Student student = studentRepo.findByStudentNumber(studentNumber);
        if (student == null) {
            throw new RuntimeException("Student with number " + studentNumber + " not found");
        }

        student.setStudentIdNumber(dto.getStudentIdNumber());
        student.setFirstName(dto.getFirstName());
        student.setLastName(dto.getLastName());
        student.setIntake(dto.getIntake());
        student.setAddress(dto.getAddress());
        student.setBirthday(dto.getBirthday());
        student.setDegreeProgram(DegreeProgram.valueOf(dto.getDegreeProgram()));
        student.setStatus(StudentStatus.valueOf(dto.getStatus()));

        studentRepo.save(student);

        // Reuse existing method to return full updated details
        return getAllStudentDetailsByID(studentNumber);
    }

    @Override
    public long countStudents() {
        return studentRepo.count();

    }
}
