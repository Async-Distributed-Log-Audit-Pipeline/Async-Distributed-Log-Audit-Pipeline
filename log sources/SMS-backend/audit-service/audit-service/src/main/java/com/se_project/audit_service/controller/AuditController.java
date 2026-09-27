package com.se_project.audit_service.controller;

import com.se_project.audit_service.dto.AuditLogRequest;
import com.se_project.audit_service.entity.AuditLog;
import com.se_project.audit_service.repo.AuditLogRepo;
import com.se_project.audit_service.service.AuditService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@RestController
@RequestMapping("/api/v1/audit")
@RequiredArgsConstructor
@Slf4j
public class AuditController {

    @Autowired
    private  AuditService auditService;

    @Autowired
    private AuditLogRepo auditLogRepo;

    @Value("${app.logs.directory:logs}")
    private String logsDirectory;

    @PostMapping("/log")
    public ResponseEntity<AuditLog> logAction(@RequestBody AuditLogRequest request) {
        log.info("Received audit log request: {}", request.getAction());
        AuditLog saved = auditService.logAction(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @GetMapping("/admin/{adminEmail}")
    public ResponseEntity<List<AuditLog>> getLogsByAdmin(@PathVariable String adminEmail) {
        List<AuditLog> logs = auditService.getLogsByAdmin(adminEmail);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/target/{targetEntity}/{targetId}")
    public ResponseEntity<List<AuditLog>> getLogsByTarget(
            @PathVariable String targetEntity,
            @PathVariable String targetId) {
        List<AuditLog> logs = auditService.getLogsByTarget(targetEntity, targetId);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/all")
    public ResponseEntity<List<AuditLog>> getAllLogs() {
        List<AuditLog> logs = auditService.getAllLogs();
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/all-logs")
    public List<AuditLog> getAllLogs(@RequestParam(defaultValue = "10") int limit) {
        return auditLogRepo.findAll(PageRequest.of(0, limit)).getContent();
    }

    @GetMapping(path = "/count")
    public ResponseEntity<Long> getAuditLogCount() {
        long count = auditService.getAuditLogCount();
        return ResponseEntity.ok(count);
    }

    @GetMapping(value = "/log-files/download", produces = "application/zip")
    public ResponseEntity<StreamingResponseBody> downloadRuntimeLogs() throws IOException {
        Path directory = Paths.get(logsDirectory).toAbsolutePath().normalize();
        if (!Files.isDirectory(directory)) {
            return ResponseEntity.notFound().build();
        }

        List<Path> logFiles;
        try (var paths = Files.list(directory)) {
            logFiles = paths
                    .filter(path -> Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
                    .filter(path -> path.getFileName().toString().endsWith(".jsonl"))
                    .sorted()
                    .toList();
        }
        if (logFiles.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        StreamingResponseBody responseBody = outputStream -> {
            try (ZipOutputStream zipOutputStream = new ZipOutputStream(outputStream)) {
                for (Path logFile : logFiles) {
                    zipOutputStream.putNextEntry(new ZipEntry(logFile.getFileName().toString()));
                    Files.copy(logFile, zipOutputStream);
                    zipOutputStream.closeEntry();
                }
            }
        };

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/zip"))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"runtime-logs.zip\"")
                .body(responseBody);
    }
}