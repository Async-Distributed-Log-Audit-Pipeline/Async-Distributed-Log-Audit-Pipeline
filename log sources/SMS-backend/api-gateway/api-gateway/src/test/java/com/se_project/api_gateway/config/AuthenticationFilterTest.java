package com.se_project.api_gateway.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class AuthenticationFilterTest {

    @InjectMocks
    private AuthenticationFilter authenticationFilter;

    @Mock
    private ServerWebExchange exchange;

    @Mock
    private GatewayFilterChain chain;

    @Mock
    private ServerHttpRequest request;

    @Mock
    private ServerHttpResponse response;

    @Mock
    private HttpHeaders headers;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(authenticationFilter, "secret", "5367566B59703373367639792F423F4528482B4D6251655468576D5A71347437");
        when(exchange.getRequest()).thenReturn(request);
        when(request.getHeaders()).thenReturn(headers);
    }

    @Test
    void apply_ReturnsUnauthorized_WhenAuthHeaderMissing() {
        when(headers.containsKey("Authorization")).thenReturn(false);
        when(exchange.getResponse()).thenReturn(response);
        when(response.setStatusCode(HttpStatus.UNAUTHORIZED)).thenReturn(true);
        when(response.setComplete()).thenReturn(Mono.empty());

        AuthenticationFilter.Config config = new AuthenticationFilter.Config();
        GatewayFilter filter = authenticationFilter.apply(config);

        filter.filter(exchange, chain).block();

        verify(response).setStatusCode(HttpStatus.UNAUTHORIZED);
        verify(chain, never()).filter(any());
    }

    @Test
    void apply_ReturnsUnauthorized_WhenInvalidFormat() {
        when(headers.containsKey("Authorization")).thenReturn(true);
        when(headers.getFirst("Authorization")).thenReturn("InvalidToken");
        when(exchange.getResponse()).thenReturn(response);
        when(response.setStatusCode(HttpStatus.UNAUTHORIZED)).thenReturn(true);
        when(response.setComplete()).thenReturn(Mono.empty());

        AuthenticationFilter.Config config = new AuthenticationFilter.Config();
        GatewayFilter filter = authenticationFilter.apply(config);

        filter.filter(exchange, chain).block();

        verify(response).setStatusCode(HttpStatus.UNAUTHORIZED);
        verify(chain, never()).filter(any());
    }
}
