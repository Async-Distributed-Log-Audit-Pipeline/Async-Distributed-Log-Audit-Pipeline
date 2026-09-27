package com.se_project.api_gateway.config;

import lombok.RequiredArgsConstructor;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@RequiredArgsConstructor
public class GatewayConfig {

    private final AuthenticationFilter authenticationFilter;

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                // Auth Service - No authentication required
//                .route("auth-service", r -> r
//                        .path("/api/v1/auth/**")
//                        .uri("lb://auth-service"))
                // Auth endpoints - No JWT required for login/register
                .route("auth-public", r -> r
                        .path("/api/v1/auth/login", "/api/v1/auth/register")
                        .uri("lb://auth-service"))

                // Logout - JWT required (goes through auth filter)
                .route("auth-logout", r -> r
                        .path("/api/v1/auth/logout")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://auth-service"))

                // Validate - No JWT required (used internally)
                .route("auth-validate", r -> r
                        .path("/api/v1/auth/validate")
                        .uri("lb://auth-service"))

                // Get Admin - JWT required
                .route("auth-get-admin", r -> r
                        .path("/api/v1/auth/get-admin/**")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://auth-service"))

                // Get Admin - JWT required
                .route("auth-update-admin", r -> r
                        .path("/api/v1/auth/update/**")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://auth-service"))

                // Student Service - Authentication required
                .route("student-service", r -> r
                        .path("/api/v1/student/**")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://student-service"))

                // Course Service - Authentication required
                .route("course-service", r -> r
                        .path("/api/v1/course/**")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://course-service"))

                .route("audit-service", r -> r
                        .path("/api/v1/audit/**")
                        .filters(f -> f.filter(authenticationFilter.apply(new AuthenticationFilter.Config())))
                        .uri("lb://audit-service"))

                .build();
    }
}