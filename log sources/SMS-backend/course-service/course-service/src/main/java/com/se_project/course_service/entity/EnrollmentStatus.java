package com.se_project.course_service.entity;

public enum EnrollmentStatus {
    ENROLLED("Currently Enrolled"),
    COMPLETED("Completed"),
    DROPPED("Dropped"),
    FAILED("Failed"),
    WITHDRAWN("Withdrawn");

    private final String displayName;

    EnrollmentStatus(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }
}
