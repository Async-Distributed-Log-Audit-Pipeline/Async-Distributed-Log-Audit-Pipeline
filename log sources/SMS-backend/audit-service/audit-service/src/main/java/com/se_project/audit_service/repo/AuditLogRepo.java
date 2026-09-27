package com.se_project.audit_service.repo;

import com.se_project.audit_service.entity.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
@EnableJpaRepositories
public interface AuditLogRepo extends JpaRepository<AuditLog, Long> {

    List<AuditLog> findByAdminEmailOrderByCreatedAtDesc(String adminEmail);

    List<AuditLog> findByTargetEntityAndTargetIdOrderByCreatedAtDesc(
            String targetEntity, String targetId);

    List<AuditLog> findAllByOrderByCreatedAtDesc();
}