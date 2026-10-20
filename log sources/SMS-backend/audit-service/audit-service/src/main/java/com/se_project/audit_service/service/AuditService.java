package com.se_project.audit_service.service;

import com.se_project.audit_service.dto.AuditLogRequest;
import com.se_project.audit_service.entity.AuditLog;
import com.se_project.audit_service.repo.AuditLogRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditService {

//    private final com.se_project.audit_service.repository.AuditLogRepo auditLogRepository;

    @Autowired
private AuditLogRepo auditLogRepo;

    @Transactional
    public AuditLog logAction(AuditLogRequest request) {
        log.info("Logging action: {} by {}", request.getAction(), request.getAdminEmail());

        AuditLog auditLog = new AuditLog();
        auditLog.setAdminEmail(request.getAdminEmail());
        auditLog.setAction(request.getAction());
        auditLog.setServiceName(request.getServiceName());
        auditLog.setTargetEntity(request.getTargetEntity());
        auditLog.setTargetId(request.getTargetId());
        auditLog.setDetails(request.getDetails());
        auditLog.setIpAddress(request.getIpAddress());
        auditLog.setStatus(request.getStatus() != null ? request.getStatus() : "SUCCESS");
        auditLog.setErrorMessage(request.getErrorMessage());

        return auditLogRepo.save(auditLog);
    }

    public List<AuditLog> getLogsByAdmin(String adminEmail) {
        return auditLogRepo.findByAdminEmailOrderByCreatedAtDesc(adminEmail);
    }

    public List<AuditLog> getLogsByTarget(String targetEntity, String targetId) {
        return auditLogRepo.findByTargetEntityAndTargetIdOrderByCreatedAtDesc(
                targetEntity, targetId);
    }

    public List<AuditLog> getAllLogs() {
        return auditLogRepo.findAllByOrderByCreatedAtDesc();
    }

    public long getAuditLogCount() {
        return auditLogRepo.count();
    }
}