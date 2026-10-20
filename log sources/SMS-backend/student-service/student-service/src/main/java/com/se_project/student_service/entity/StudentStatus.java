package com.se_project.student_service.entity;

public enum StudentStatus {
    ACTIVE("Active"),
    INACTIVE("Inactive"),
    GRADUATED("Graduated"),
    WITHDRAWN("Withdrawn"),
    TRANSFERRED("Transferred"),
    SUSPENDED("Suspended");

    private final String displayName;

    StudentStatus(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }}
