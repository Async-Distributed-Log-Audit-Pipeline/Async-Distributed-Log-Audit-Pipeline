package com.se_project.auth_service.util;

import com.se_project.auth_service.dto.AuditLogRequest;
import com.se_project.auth_service.dto.LoginRequest;
import com.se_project.auth_service.dto.LoginResponse;
import com.se_project.auth_service.dto.RegisterAdminRequest;
import com.se_project.auth_service.entity.AdminUser;
import com.se_project.auth_service.repo.AdminUserRepo;
import com.se_project.auth_service.service.AuditServiceClient;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Optional;

@Aspect
@Component
@RequiredArgsConstructor
@Slf4j
public class AuditAspect {

    private final AuditServiceClient auditServiceClient;
    private final AdminUserRepo adminUserRepository;  // ← Add this!

    @Around("@annotation(auditable)")
    public Object logAroundMethod(ProceedingJoinPoint joinPoint, Auditable auditable) throws Throwable {

        HttpServletRequest request = getCurrentRequest();
        String ipAddress = getIpAddress(request);

        Object result = null;
        String status = "SUCCESS";
        String errorMessage = null;
        String adminEmail = null;

        try {
            result = joinPoint.proceed();
            adminEmail = extractAdminEmail(request, auditable.action(), joinPoint.getArgs(), result);
            log.info("Method {} executed successfully by {}", auditable.action(), adminEmail);

        } catch (Exception e) {
            status = "FAILURE";
            errorMessage = e.getMessage();
            adminEmail = extractAdminEmail(request, auditable.action(), joinPoint.getArgs(), null);
            log.error("Method {} failed for {}: {}", auditable.action(), adminEmail, e.getMessage());
            throw e;

        } finally {
            try {
                String targetId = extractTargetId(result, joinPoint.getArgs());
                String details = buildDetails(auditable.action(), joinPoint.getArgs(), result, status);

                AuditLogRequest auditRequest = new AuditLogRequest(
                        adminEmail != null ? adminEmail : "system",
                        auditable.action(),
                        "auth-service",
                        auditable.entity(),
                        targetId,
                        details,
                        ipAddress,
                        status,
                        errorMessage
                );

                auditServiceClient.logAction(auditRequest);
                log.info("Audit log sent: {} - {} by {}", auditable.action(), status, adminEmail);

            } catch (Exception e) {
                log.error("Failed to send audit log", e);
            }
        }

        return result;
    }

    /**
     * Extract admin email - ALWAYS return email format
     */
    private String extractAdminEmail(HttpServletRequest request, String action,
                                     Object[] args, Object result) {

        // 1. For REGISTER_ADMIN
        if ("REGISTER_ADMIN".equals(action)) {
            if (result instanceof AdminUser) {
                return ((AdminUser) result).getEmail();
            }
            if (args != null && args.length > 0 && args[0] instanceof RegisterAdminRequest) {
                return ((RegisterAdminRequest) args[0]).getEmail();
            }
        }

        // 2. For ADMIN_LOGIN
        if ("ADMIN_LOGIN".equals(action)) {
            // Success case - get from result
            if (result instanceof LoginResponse) {
                return ((LoginResponse) result).getEmail();
            }

            // Failure case - look up email by username
            if (args != null && args.length > 0 && args[0] instanceof LoginRequest) {
                LoginRequest loginRequest = (LoginRequest) args[0];
                String username = loginRequest.getUsername();

                // Try to find admin by username and get their email
                Optional<AdminUser> adminOpt = adminUserRepository.findByUsername(username);
                if (adminOpt.isPresent()) {
                    return adminOpt.get().getEmail();  // ✅ Return actual email!
                }

                // If admin not found, return "unknown-" + username
                return "unknown-" + username + "@attempted.login";
            }
        }

        // 3. For ADMIN_LOGOUT
        if ("ADMIN_LOGOUT".equals(action)) {
            if (args != null && args.length > 0 && args[0] instanceof String) {
                return (String) args[0];
            }
        }

        // 4. For other operations - get from header
        String headerEmail = request.getHeader("Admin-Email");
        if (headerEmail != null) {
            return headerEmail;
        }

        return "system";
    }

    private String getIpAddress(HttpServletRequest request) {
        String ipAddress = request.getHeader("X-Forwarded-For");
        if (ipAddress == null || ipAddress.isEmpty()) {
            ipAddress = request.getRemoteAddr();
        }
        return ipAddress;
    }

    private HttpServletRequest getCurrentRequest() {
        ServletRequestAttributes attributes =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attributes.getRequest();
    }

    private String extractTargetId(Object result, Object[] args) {
        if (result instanceof AdminUser) {
            return ((AdminUser) result).getUsername();
        }
        if (result instanceof LoginResponse) {
            return ((LoginResponse) result).getUsername();
        }
        return null;
    }

    private String buildDetails(String action, Object[] args, Object result, String status) {

        if (status.equals("FAILURE")) {
            if (args != null && args.length > 0) {
                if (args[0] instanceof LoginRequest) {
                    LoginRequest req = (LoginRequest) args[0];
                    return String.format("Failed login attempt for username: %s", req.getUsername());
                }
                if (args[0] instanceof RegisterAdminRequest) {
                    RegisterAdminRequest req = (RegisterAdminRequest) args[0];
                    return String.format("Failed to register admin: %s", req.getEmail());
                }
            }
            return String.format("Failed to %s", action);
        }

        if (result instanceof AdminUser) {
            AdminUser adminUser = (AdminUser) result;
            return String.format("%s: %s %s (%s)",
                    action,
                    adminUser.getFirstName(),
                    adminUser.getLastName(),
                    adminUser.getEmail()
            );
        }

        if (result instanceof LoginResponse) {
            LoginResponse response = (LoginResponse) result;
            return String.format("Successful login: %s (%s)",
                    response.getFullName(),
                    response.getEmail()
            );
        }

        if ("ADMIN_LOGOUT".equals(action)) {
            if (args != null && args.length > 0 && args[0] instanceof String) {
                return String.format("Admin logged out: %s", args[0]);
            }
        }

        return action;
    }
}