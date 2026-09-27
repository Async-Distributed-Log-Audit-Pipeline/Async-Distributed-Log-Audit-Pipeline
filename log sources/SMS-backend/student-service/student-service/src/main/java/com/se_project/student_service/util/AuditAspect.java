package com.se_project.student_service.util;//package com.se_project.student_service.util;
//
//import com.netflix.discovery.converters.Auto;
//import com.se_project.student_service.dto.AuditLogRequest;
//import com.se_project.student_service.entity.Student;
//import com.se_project.student_service.service.AuditServiceClient;
//import lombok.RequiredArgsConstructor;
//import lombok.extern.slf4j.Slf4j;
//import org.aspectj.lang.JoinPoint;
//import org.aspectj.lang.annotation.AfterReturning;
//import org.aspectj.lang.annotation.AfterThrowing;
//import org.aspectj.lang.annotation.Aspect;
//import org.aspectj.lang.reflect.MethodSignature;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Component;
//import org.springframework.web.context.request.RequestContextHolder;
//import org.springframework.web.context.request.ServletRequestAttributes;
//
//import jakarta.servlet.http.HttpServletRequest;
//
//@Aspect
//@Component
//@RequiredArgsConstructor
//@Slf4j
//public class AuditAspect {
//
//   @Autowired
//   private AuditServiceClient auditServiceClient;
//
//    /**
//     * This runs AFTER a method with @Auditable annotation completes successfully
//     */
//    @AfterReturning(
//            pointcut = "@annotation(auditable)",
//            returning = "result"
//    )
//    public void logAfterSuccess(JoinPoint joinPoint, Auditable auditable, Object result) {
//        try {
//            // Get admin email from request header (set by API Gateway)
//            HttpServletRequest request = getCurrentRequest();
//            String adminEmail = request.getHeader("Admin-Email");
//            String ipAddress = request.getRemoteAddr();
//
//            // Get method parameters
//            Object[] args = joinPoint.getArgs();
//
//            // Build audit details
//            String targetId = extractTargetId(result);
//            String details = buildDetails(auditable.action(), args, result);
//
//            // Send to Audit Service
//            AuditLogRequest auditRequest = new AuditLogRequest(
//                    adminEmail,
//                    auditable.action(),
//                    "student-service",
//                    auditable.entity(),
//                    targetId,
//                    details,
//                    ipAddress,
//                    "SUCCESS",
//                    null
//            );
//
//            auditServiceClient.logAction(auditRequest);
//            log.info("Audit log sent: {} on {}", auditable.action(), auditable.entity());
//
//        } catch (Exception e) {
//            log.error("Failed to send audit log", e);
//            // Don't throw exception - audit failure shouldn't break business logic
//        }
//    }
//
//    /**
//     * This runs AFTER a method with @Auditable throws an exception
//     */
//    @AfterThrowing(
//            pointcut = "@annotation(auditable)",
//            throwing = "exception"
//    )
//    public void logAfterError(JoinPoint joinPoint, Auditable auditable, Exception exception) {
//        try {
//            HttpServletRequest request = getCurrentRequest();
//            String adminEmail = request.getHeader("Admin-Email");
//            String ipAddress = request.getRemoteAddr();
//
//            Object[] args = joinPoint.getArgs();
//            String details = "Failed: " + auditable.action();
//
//            AuditLogRequest auditRequest = new AuditLogRequest(
//                    adminEmail,
//                    auditable.action(),
//                    "student-service",
//                    auditable.entity(),
//                    null,
//                    details,
//                    ipAddress,
//                    "FAILURE",
//                    exception.getMessage()
//            );
//
//            auditServiceClient.logAction(auditRequest);
//            log.info("Audit log sent for failed operation: {}", auditable.action());
//
//        } catch (Exception e) {
//            log.error("Failed to send audit log for error", e);
//        }
//    }
//
//    private HttpServletRequest getCurrentRequest() {
//        ServletRequestAttributes attributes =
//                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
//        return attributes.getRequest();
//    }
//
//    private String extractTargetId(Object result) {
//        if (result instanceof Student) {
//            return ((Student) result).getStudentNumber();
//        }
//        return null;
//    }
//
//    private String buildDetails(String action, Object[] args, Object result) {
//        if (result instanceof Student) {
//            Student student = (Student) result;
//            return String.format("%s: %s %s (ID: %s)",
//                    action,
//                    student.getFirstName(),
//                    student.getLastName(),
//                    student.getStudentNumber()
//            );
//        }
//        return action;
//    }
//}

//package com.se_project.student_service.aspect;
//
//import com.se_project.student_service.annotation.Auditable;
//import com.se_project.student_service.client.AuditServiceClient;

import com.se_project.student_service.dto.AuditLogRequest;
import com.se_project.student_service.entity.Student;
import com.se_project.student_service.service.AuditServiceClient;
import com.se_project.student_service.util.Auditable;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Aspect
@Component
@RequiredArgsConstructor
@Slf4j
public class AuditAspect {

   // private final AuditServiceClient auditServiceClient;

    @Autowired
    private AuditServiceClient auditServiceClient;

    /**
     * @Around wraps the entire method execution
     * Catches BOTH success and failure
     */
    @Around("@annotation(auditable)")
    public Object logAroundMethod(ProceedingJoinPoint joinPoint, Auditable auditable) throws Throwable {

        HttpServletRequest request = getCurrentRequest();
        String adminEmail = request.getHeader("Admin-Email");
        String ipAddress = request.getRemoteAddr();

        Object result = null;
        String status = "SUCCESS";
        String errorMessage = null;

        try {
            // Execute the actual method
            result = joinPoint.proceed();

            // Method succeeded
            log.info("Method {} executed successfully", auditable.action());

        } catch (Exception e) {
            // Method failed
            status = "FAILURE";
            errorMessage = e.getMessage();
            log.error("Method {} failed: {}", auditable.action(), e.getMessage());

            // Re-throw the exception so it reaches the controller
            throw e;

        } finally {
            // ALWAYS log audit (success or failure)
            try {
                String targetId = extractTargetId(result);
                String details = buildDetails(auditable.action(), joinPoint.getArgs(), result, status);

                AuditLogRequest auditRequest = new AuditLogRequest(
                        adminEmail,
                        auditable.action(),
                        "student-service",
                        auditable.entity(),
                        targetId,
                        details,
                        ipAddress,
                        status,
                        errorMessage
                );

                auditServiceClient.logAction(auditRequest);
                log.info("Audit log sent: {} - {}", auditable.action(), status);

            } catch (Exception e) {
                log.error("Failed to send audit log", e);
            }
        }

        return result;
    }

    private HttpServletRequest getCurrentRequest() {
        ServletRequestAttributes attributes =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attributes.getRequest();
    }

    private String extractTargetId(Object result) {
        if (result instanceof Student) {
            return ((Student) result).getStudentNumber();
        }
        return null;
    }

    private String buildDetails(String action, Object[] args, Object result, String status) {
        if (status.equals("FAILURE")) {
            return String.format("Failed to %s", action);
        }

        if (result instanceof Student) {
            Student student = (Student) result;
            return String.format("%s: %s %s (ID: %s)",
                    action,
                    student.getFirstName(),
                    student.getLastName(),
                    student.getStudentNumber()
            );
        }
        return action;
    }
}