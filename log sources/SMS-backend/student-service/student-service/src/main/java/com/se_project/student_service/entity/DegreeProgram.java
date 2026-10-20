package com.se_project.student_service.entity;

public enum DegreeProgram {

    SOFTWARE_ENGINEERING("Software Engineering", "SE", 4),
    COMPUTER_ENGINEERING("Computer Engineering", "CE", 4),
    COMPUTER_SCIENCE("Computer Science", "CS", 4),
    INFORMATION_TECHNOLOGY("Information Technology", "IT", 4),
    DATA_SCIENCE("Data Science", "DBA", 4);

    private final String displayName;
    private final String code;
    private final int durationYears;

    DegreeProgram(String displayName, String code, int durationYears) {
        this.displayName = displayName;
        this.code = code;
        this.durationYears = durationYears;
    }

    public String getDisplayName(String computerScience) {
        return displayName;
    }

    public String getCode() {
        return code;
    }

    public int getDurationYears() {
        return durationYears;
    }
}
