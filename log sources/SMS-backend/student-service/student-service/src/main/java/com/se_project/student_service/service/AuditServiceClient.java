package com.se_project.student_service.service;
import com.se_project.student_service.dto.AuditLogRequest;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "audit-service")
public interface AuditServiceClient {

    @PostMapping("/api/v1/audit/log")
    void logAction(@RequestBody AuditLogRequest request);
}