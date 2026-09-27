package com.se_project.auth_service.service;

import com.se_project.auth_service.dto.LoginRequest;
import com.se_project.auth_service.dto.LoginResponse;
import com.se_project.auth_service.dto.RegisterAdminRequest;
import com.se_project.auth_service.dto.UpdateAdminRequest;
import com.se_project.auth_service.entity.AdminUser;
import com.se_project.auth_service.entity.Role;
import com.se_project.auth_service.repo.AdminUserRepo;
import com.se_project.auth_service.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class AuthServiceTest {

    @Mock
    private AdminUserRepo adminUserRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private JwtUtil jwtUtil;

    @InjectMocks
    private AuthService authService;

    private AdminUser adminUser;
    private RegisterAdminRequest registerRequest;

    @BeforeEach
    void setUp() {
        adminUser = new AdminUser();
        adminUser.setUsername("admin");
        adminUser.setEmail("admin@example.com");
        adminUser.setPassword("encodedPassword");
        adminUser.setRole(Role.ADMIN);
        adminUser.setIsActive(true);
        adminUser.setFirstName("John");
        adminUser.setLastName("Doe");

        registerRequest = new RegisterAdminRequest();
        registerRequest.setUsername("admin");
        registerRequest.setEmail("admin@example.com");
        registerRequest.setPassword("password");
        registerRequest.setFirstName("John");
        registerRequest.setLastName("Doe");
    }

    @Test
    void registerAdmin_Success() {
        when(adminUserRepository.existsByUsername(anyString())).thenReturn(false);
        when(adminUserRepository.existsByEmail(anyString())).thenReturn(false);
        when(passwordEncoder.encode(anyString())).thenReturn("encodedPassword");
        when(adminUserRepository.save(any(AdminUser.class))).thenReturn(adminUser);

        AdminUser savedAdmin = authService.registerAdmin(registerRequest);

        assertNotNull(savedAdmin);
        assertEquals("admin@example.com", savedAdmin.getEmail());
        verify(adminUserRepository, times(1)).save(any(AdminUser.class));
    }

    @Test
    void registerAdmin_ThrowsException_WhenUsernameExists() {
        when(adminUserRepository.existsByUsername(anyString())).thenReturn(true);

        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            authService.registerAdmin(registerRequest);
        });

        assertEquals("Username already exists", exception.getMessage());
        verify(adminUserRepository, never()).save(any(AdminUser.class));
    }

    @Test
    void login_Success() {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("password");

        when(adminUserRepository.findByUsername("admin")).thenReturn(Optional.of(adminUser));
        when(passwordEncoder.matches("password", "encodedPassword")).thenReturn(true);
        when(jwtUtil.generateToken(anyString(), anyString(), anyString())).thenReturn("mockedToken");

        LoginResponse response = authService.login(loginRequest);

        assertNotNull(response);
        assertEquals("mockedToken", response.getToken());
        assertEquals("admin@example.com", response.getEmail());
    }

    @Test
    void login_ThrowsException_WhenInvalidCredentials() {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("wrongPassword");

        when(adminUserRepository.findByUsername("admin")).thenReturn(Optional.of(adminUser));
        when(passwordEncoder.matches("wrongPassword", "encodedPassword")).thenReturn(false);

        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            authService.login(loginRequest);
        });

        assertEquals("Invalid username or password", exception.getMessage());
    }

    @Test
    void updateAdmin_Success() {
        UpdateAdminRequest updateRequest = new UpdateAdminRequest();
        updateRequest.setFirstName("Jane");
        updateRequest.setLastName("Smith");

        when(adminUserRepository.findByUsername("admin")).thenReturn(Optional.of(adminUser));
        when(adminUserRepository.save(any(AdminUser.class))).thenReturn(adminUser);

        AdminUser updatedAdmin = authService.updateAdmin("admin", updateRequest);

        assertNotNull(updatedAdmin);
        assertEquals("Jane", updatedAdmin.getFirstName());
        assertEquals("Smith", updatedAdmin.getLastName());
        verify(adminUserRepository, times(1)).save(adminUser);
    }
}
