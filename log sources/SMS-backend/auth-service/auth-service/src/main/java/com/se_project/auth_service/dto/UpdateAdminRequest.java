package com.se_project.auth_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class UpdateAdminRequest {
    private String firstName;
    private String lastName;
    private String email;
}
