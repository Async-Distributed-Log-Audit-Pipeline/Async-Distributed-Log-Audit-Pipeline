package com.se_project.auth_service.service;

import com.se_project.auth_service.dto.LoginRequest;
import com.se_project.auth_service.dto.LoginResponse;
import com.se_project.auth_service.dto.RegisterAdminRequest;
import com.se_project.auth_service.dto.UpdateAdminRequest;
import com.se_project.auth_service.entity.AdminUser;
import com.se_project.auth_service.entity.Role;
import com.se_project.auth_service.repo.AdminUserRepo;
import com.se_project.auth_service.util.Auditable;
import com.se_project.auth_service.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthService {

    @Autowired
    private  AdminUserRepo adminUserRepository;

    @Autowired
    private  PasswordEncoder passwordEncoder;

    @Autowired
    private  JwtUtil jwtUtil;

    @Transactional
    @Auditable(action = "REGISTER_ADMIN", entity = "AdminUser")
    public AdminUser registerAdmin(RegisterAdminRequest request) {
        log.info("Registering new admin: {}", request.getEmail());

        // Check if username or email already exists
        if (adminUserRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("Username already exists");
        }

        if (adminUserRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }

        // Create new admin user
        AdminUser admin = new AdminUser();
        admin.setUsername(request.getUsername());
        admin.setEmail(request.getEmail());
        admin.setPassword(passwordEncoder.encode(request.getPassword()));
        admin.setFirstName(request.getFirstName());
        admin.setLastName(request.getLastName());
        admin.setRole(Role.ADMIN);  // Default role
        admin.setIsActive(true);

        AdminUser saved = adminUserRepository.save(admin);
        log.info("Successfully registered admin: {}", saved.getEmail());

        return saved;
    }

    @Transactional
    @Auditable(action = "ADMIN_LOGIN", entity = "AdminUser")
    public LoginResponse login(LoginRequest request) {
        log.info("Login attempt for: {}", request.getUsername());

        // Find admin by username
        AdminUser admin = adminUserRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new RuntimeException("Invalid username or password"));

        // Check if account is active
        if (!admin.getIsActive()) {
            throw new RuntimeException("Account is deactivated");
        }

        // Verify password
        if (!passwordEncoder.matches(request.getPassword(), admin.getPassword())) {
            throw new RuntimeException("Invalid username or password");
        }

        // Generate JWT token
        String token = jwtUtil.generateToken(
                admin.getUsername(),
                admin.getEmail(),
                admin.getRole().toString()
        );

        log.info("Login successful for: {}", admin.getEmail());

        return new LoginResponse(
                token,
                admin.getUsername(),
                admin.getEmail(),
                admin.getRole().toString(),
                admin.getFirstName() + " " + admin.getLastName()
        );
    }

    public Boolean validateToken(String token) {
        return jwtUtil.validateToken(token);
    }

    public String extractEmail(String token) {
        return jwtUtil.extractEmail(token);
    }

    public String extractRole(String token) {
        return jwtUtil.extractRole(token);
    }

    @Auditable(action = "ADMIN_LOGOUT", entity = "AdminUser")
    public void logout(String adminEmail, String ipAddress) {
        log.info("Logout for: {}", adminEmail);

        // With JWT, there's no server-side session to invalidate
        // The audit log is created automatically by @Auditable

        // Optional: You could add the token to a blacklist here
        // if you want to prevent its further use
    }

    public AdminUser getAdminByUsername(String username) {
        return adminUserRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("Admin user not found"));
    }

    @Transactional
    @Auditable(action = "UPDATE_ADMIN", entity = "AdminUser")
    public AdminUser updateAdmin(String username, UpdateAdminRequest request) {
        AdminUser admin = adminUserRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("Admin user not found"));

        if (request.getFirstName() != null) {
            admin.setFirstName(request.getFirstName());
        }
        if (request.getLastName() != null) {
            admin.setLastName(request.getLastName());
        }
      if(request.getEmail() != null) {
            if (adminUserRepository.existsByEmail(request.getEmail())) {
                throw new RuntimeException("Email already exists");
            }
            admin.setEmail(request.getEmail());
      }

        return adminUserRepository.save(admin);
    }
}