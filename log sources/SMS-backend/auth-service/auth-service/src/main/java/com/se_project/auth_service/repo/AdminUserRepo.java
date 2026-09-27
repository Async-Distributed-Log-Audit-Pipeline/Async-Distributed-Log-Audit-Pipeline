package com.se_project.auth_service.repo;

import com.se_project.auth_service.entity.AdminUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
@EnableJpaRepositories
public interface AdminUserRepo extends JpaRepository<AdminUser,Long> {

    Optional<AdminUser> findByUsername(String username);

    Optional<AdminUser> findByEmail(String email);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);

    //Optional<Object> findByUsername(String username);
}
