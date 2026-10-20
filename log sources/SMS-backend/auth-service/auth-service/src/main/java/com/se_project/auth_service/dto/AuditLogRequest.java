package com.se_project.auth_service.dto;


import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
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
