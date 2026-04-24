class GradeService:
    """
    Handles grade submission, cumulative GPA calculation, and academic standing rules enforcement.
    """
    
    def submit_grade(instructor_id: str, student_id: str, course_id: str, letter_grade: str) -> bool:
        """
        Input: instructor_id string, student_id string, course_id string, letter_grade string (e.g., 'A', 'B+', 'C').
        Output: Boolean indicating successful submission.
        Procedure:
        1. Verify course is in grading phase.
        2. Save the grade for the student.
        3. Update student's GPA.
        """
        pass
    
    def calculate_gpa(student_id: str) -> float:
        """
        Input: student_id string.
        Output: Float representing the updated cumulative GPA.
        Procedure:
        1. Get all completed course grades.
        2. Calculate average based on credits.
        3. Save new GPA.
        """
        pass        
    
    def check_academic_standing(student_id: str) -> str:
        """
        Input: student_id string.
        Output: Standing status string ('Good', 'Warning', 'Suspension', 'Termination').
        Procedure:
        1. Check current GPA against minimum requirements.
        2. Issue warnings or suspend account if GPA is too low.
        """
        pass     
