package com.se_project.auth_service.util;

import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.util.Base64;

public class JwtKeyGenarator {
    public static void main(String[] args) {

        SecretKey key = Keys.secretKeyFor(io.jsonwebtoken.SignatureAlgorithm.HS512);
        String base64Key = Base64.getEncoder().encodeToString(key.getEncoded());
        System.out.println("Your new SECRET_KEY (Base64): " + base64Key);
    }
}
