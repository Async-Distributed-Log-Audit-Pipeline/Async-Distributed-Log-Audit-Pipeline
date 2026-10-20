package com.se_project.course_service.entity;

public enum Grade {
    A_PLUS("A+", 4.0),
    A("A", 4.0),
    A_MINUS("A-", 3.7),
    B_PLUS("B+", 3.3),
    B("B", 3.0),
    B_MINUS("B-", 2.7),
    C_PLUS("C+", 2.3),
    C("C", 2.0),
    C_MINUS("C-", 1.7),
    D("D", 1.0),
    F("F", 0.0),
    INCOMPLETE("I", null),
    PASS("P", null),
    NOT_GRADED("NG", null);

    private final String displayName;
    private final Double gradePoint;

    Grade(String displayName, Double gradePoint) {
        this.displayName = displayName;
        this.gradePoint = gradePoint;
    }

    public String getDisplayName() {
        return displayName;
    }

    public Double getGradePoint() {
        return gradePoint;
    }
}
