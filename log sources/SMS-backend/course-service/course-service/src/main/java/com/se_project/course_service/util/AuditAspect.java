package com.se_project.course_service.util;

import com.se_project.course_service.dto.AuditLogRequest;
import com.se_project.course_service.entity.Course;
import com.se_project.course_service.service.AuditServiceClient;
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
        if (result instanceof Course) {
            return ((Course) result).getCourseName();
        }
        return null;
    }

    private String buildDetails(String action, Object[] args, Object result, String status) {
        if (status.equals("FAILURE")) {
            return String.format("Failed to %s", action);
        }

        if (result instanceof Course) {
            Course course = (Course) result;
            return String.format("%s: %s %s (ID: %s)",
                    action,
                    course.getCourseName(),
                    course.getCourseCode()
                   // course.getStudentNumber()
            );
        }
        return action;
    }
}
