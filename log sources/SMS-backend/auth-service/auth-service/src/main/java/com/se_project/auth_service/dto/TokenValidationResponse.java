package com.se_project.auth_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class TokenValidationResponse {
    private boolean valid;
    private String email;
    private String role;
}
