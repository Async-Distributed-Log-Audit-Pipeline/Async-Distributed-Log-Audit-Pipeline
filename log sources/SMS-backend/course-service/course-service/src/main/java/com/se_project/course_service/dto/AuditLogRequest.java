package com.se_project.course_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AuditLogRequest {
    private String adminEmail;
    private String action;
    private String serviceName;
    private String targetEntity;
    private String targetId;
    private String details;
    private String ipAddress;
    private String status;
    private String errorMessage;
}