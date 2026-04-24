class EnrollmentService:
    """
    Manages student course registration, timing conflicts, and waitlists.
    """

    def enroll_student(student_id: str, course_id: str) -> str:
        """
        Input: student_id string, course_id string.
        Output: Status string indicating the outcome ('Enrolled', 'Waitlisted', 'Failed_Conflict', 'Failed_Limit').
        """
        pass      

   def drop_course(student_id: str, course_id: str) -> bool:
        """
        Input: student_id string, course_id string.
        Output: Boolean indicating successful removal.
        """
        pass    

   def check_time_conflict(existing_schedules: list, target_schedule: list) -> bool:
        """
        Input: existing_schedules list of time intervals, target_schedule list of time intervals.
        Output: Boolean True if a conflict in class times exists, else False.
        """
        pass    

   def process_waitlist(course_id: str) -> str:
        """
        Input: course_id string.
        Output: student_id string of the user popped from the waitlist, or None if the waitlist is empty.
        """
        pass
