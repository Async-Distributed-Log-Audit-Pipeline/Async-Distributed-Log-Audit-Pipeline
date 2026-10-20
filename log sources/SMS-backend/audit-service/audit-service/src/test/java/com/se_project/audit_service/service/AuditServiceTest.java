package com.se_project.audit_service.service;

import com.se_project.audit_service.dto.AuditLogRequest;
import com.se_project.audit_service.entity.AuditLog;
import com.se_project.audit_service.repo.AuditLogRepo;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class AuditServiceTest {

    @Mock
    private AuditLogRepo auditLogRepo;

    @InjectMocks
    private AuditService auditService;

    private AuditLogRequest auditRequest;
    private AuditLog auditLog;

    @BeforeEach
    void setUp() {
        auditRequest = new AuditLogRequest();
        auditRequest.setAdminEmail("admin@example.com");
        auditRequest.setAction("LOGIN");
        auditRequest.setServiceName("AUTH-SERVICE");
        auditRequest.setTargetEntity("AdminUser");
        auditRequest.setIpAddress("127.0.0.1");

        auditLog = new AuditLog();
        auditLog.setAdminEmail("admin@example.com");
        auditLog.setAction("LOGIN");
    }

    @Test
    void logAction_Success() {
        when(auditLogRepo.save(any(AuditLog.class))).thenReturn(auditLog);

        AuditLog savedLog = auditService.logAction(auditRequest);

        assertNotNull(savedLog);
        assertEquals("LOGIN", savedLog.getAction());
        verify(auditLogRepo, times(1)).save(any(AuditLog.class));
    }

    @Test
    void getLogsByAdmin_ReturnsList() {
        when(auditLogRepo.findByAdminEmailOrderByCreatedAtDesc("admin@example.com"))
                .thenReturn(Collections.singletonList(auditLog));

        List<AuditLog> logs = auditService.getLogsByAdmin("admin@example.com");

        assertFalse(logs.isEmpty());
        assertEquals(1, logs.size());
        assertEquals("admin@example.com", logs.get(0).getAdminEmail());
    }

    @Test
    void getAllLogs_ReturnsList() {
        when(auditLogRepo.findAllByOrderByCreatedAtDesc())
                .thenReturn(Collections.singletonList(auditLog));

        List<AuditLog> logs = auditService.getAllLogs();

        assertFalse(logs.isEmpty());
        assertEquals(1, logs.size());
    }

    @Test
    void getAuditLogCount_ReturnsCount() {
        when(auditLogRepo.count()).thenReturn(10L);

        long count = auditService.getAuditLogCount();

        assertEquals(10L, count);
    }
}
