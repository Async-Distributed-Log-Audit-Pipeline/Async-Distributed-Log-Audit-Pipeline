package com.se_project.audit_service.exception;

//package com.se_project.audit_service.exception;
//
//import com.se_project.audit_service.dto.AuditLogRequest;
//import com.se_project.audit_service.service.AuditService;
//import jakarta.servlet.http.HttpServletRequest;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.http.HttpStatus;
//import org.springframework.http.ResponseEntity;
//import org.springframework.http.converter.HttpMessageNotReadableException;
//import org.springframework.web.bind.MethodArgumentNotValidException;
//import org.springframework.web.bind.annotation.ControllerAdvice;
//import org.springframework.web.bind.annotation.ExceptionHandler;
//
//@ControllerAdvice
public class GlobalExceptionHandler {
//
//    @Autowired
//    private AuditService auditService;
//
//    // This handles bad formats, including Date formatting issues
//    @ExceptionHandler(HttpMessageNotReadableException.class)
//    public ResponseEntity<Object> handleHttpMessageNotReadable(
//            HttpMessageNotReadableException ex, HttpServletRequest request) {
//
//        // Explicitly log this as a failure in the Audit Table
//        auditService.logAction(new AuditLogRequest(
//                "SYSTEM", // Or get from SecurityContext if possible
//                "REQUEST_DESERIALIZATION_ERROR",
//                "AUDIT_SERVICE",
//                "SYSTEM",
//                "N/A",
//                "Invalid request format: " + ex.getMostSpecificCause().getMessage(),
//                request.getRemoteAddr(),
//                "FAILURE",
//                ex.getClass().getSimpleName()
//        ));
//
//        return new ResponseEntity<>("Invalid request format", HttpStatus.BAD_REQUEST);
//    }
//
//    // This handles validation errors (e.g. @NotBlank, @Min, @Size)
//    @ExceptionHandler(MethodArgumentNotValidException.class)
//    public ResponseEntity<Object> handleValidationExceptions(
//            MethodArgumentNotValidException ex, HttpServletRequest request) {
//
//        auditService.logAction(new AuditLogRequest(
//                "SYSTEM",
//                "VALIDATION_FAILURE",
//                "AUDIT_SERVICE",
//                "SYSTEM",
//                "N/A",
//                "Validation failed for fields: " + ex.getBindingResult().getFieldErrors(),
//                request.getRemoteAddr(),
//                "FAILURE",
//                "Validation Error"
//        ));
//
//        return new ResponseEntity<>(ex.getBindingResult().getAllErrors(), HttpStatus.BAD_REQUEST);
//    }
}
