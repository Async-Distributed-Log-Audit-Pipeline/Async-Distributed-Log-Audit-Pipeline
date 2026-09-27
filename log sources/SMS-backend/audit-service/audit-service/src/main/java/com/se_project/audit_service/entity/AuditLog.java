package com.se_project.audit_service.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "audit_logs")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "admin_email", nullable = false)
    private String adminEmail;

    @Column(name = "action", nullable = false)
    private String action;  // CREATE_STUDENT, UPDATE_ENROLLMENT, etc.

    @Column(name = "service_name")
    private String serviceName;

    @Column(name = "target_entity")
    private String targetEntity;

    @Column(name = "target_id")
    private String targetId;  // Student number, enrollment ID

    @Column(name = "details", columnDefinition = "TEXT")
    private String details;

    @Column(name = "ip_address")
    private String ipAddress;

    @Column(name = "status")
    private String status;  // SUCCESS, FAILURE

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;  // If operation failed

    @CreationTimestamp
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}