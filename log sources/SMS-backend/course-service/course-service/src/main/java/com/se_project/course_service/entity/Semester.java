package com.se_project.course_service.entity;

public enum Semester {
    SEMESTER_1("Semester 1"),
    SEMESTER_2("Semester 2"),
    SEMESTER_3("Semester 3"),
    SEMESTER_4("Semester 4"),
    SEMESTER_5("Semester 5"),
    SEMESTER_6("Semester 6"),
    SEMESTER_7("Semester 7"),
    SEMESTER_8("Semester 8"),
    SUMMER("Summer Semester");

    private final String displayName;

    Semester(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }
}
