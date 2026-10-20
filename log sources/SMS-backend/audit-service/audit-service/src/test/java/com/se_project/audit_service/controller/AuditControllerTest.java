package com.se_project.audit_service.controller;

import com.se_project.audit_service.repo.AuditLogRepo;
import com.se_project.audit_service.service.AuditService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.ByteArrayOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@ExtendWith(MockitoExtension.class)
class AuditControllerTest {

    @TempDir
    Path logsDirectory;

    @Mock
    private AuditService auditService;

    @Mock
    private AuditLogRepo auditLogRepo;

    @InjectMocks
    private AuditController auditController;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(auditController, "logsDirectory", logsDirectory.toString());
    }

    @Test
    void downloadRuntimeLogsReturnsJsonlFilesAsZip() throws Exception {
        Files.writeString(logsDirectory.resolve("student-service.jsonl"), "{\"level\":\"INFO\"}\n");
        Files.writeString(logsDirectory.resolve("readme.txt"), "not a log");

        ResponseEntity<StreamingResponseBody> response = auditController.downloadRuntimeLogs();
        ByteArrayOutputStream archive = new ByteArrayOutputStream();
        assertEquals(200, response.getStatusCode().value());
        assertNotNull(response.getBody());
        response.getBody().writeTo(archive);

        try (ZipInputStream zip = new ZipInputStream(
                new java.io.ByteArrayInputStream(archive.toByteArray()))) {
            var entry = zip.getNextEntry();
            assertNotNull(entry);
            assertEquals("student-service.jsonl", entry.getName());
            assertTrue(zip.getNextEntry() == null);
        }
    }

    @Test
    void downloadRuntimeLogsReturnsNotFoundWhenNoLogsExist() throws Exception {
        ResponseEntity<StreamingResponseBody> response = auditController.downloadRuntimeLogs();

        assertEquals(404, response.getStatusCode().value());
    }
}
