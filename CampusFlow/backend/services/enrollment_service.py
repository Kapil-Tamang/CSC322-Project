    class EnrollmentService:
        """
        Manages student course registration, timing conflicts, and waitlists.
        """
        
        def enroll_student(student_id: str, course_id: str) -> str:
            """
            Input: student_id string, course_id string.
            Output: Status string indicating the outcome ('Enrolled', 'Waitlisted', 'Failed_Conflict', 'Failed_Limit').
            Procedure:
            1. Check if course registration is open.
            2. Check if student has fewer than 4 courses.
            3. Check for schedule conflicts.
            4. If full, add to waitlist. Otherwise, enroll student.
            """
            pass      
        
        def drop_course(student_id: str, course_id: str) -> bool:
            """
            Input: student_id string, course_id string.
            Output: Boolean indicating successful removal.
            Procedure:
            1. Remove student's enrollment record.
            2. Check waitlist to fill the open seat.
            """
            pass    
        
        def check_time_conflict(existing_schedules: list, target_schedule: list) -> bool:
            """
            Input: existing_schedules list of time intervals, target_schedule list of time intervals.
            Output: Boolean True if a conflict in class times exists, else False.
            Procedure:
            1. Sort all class times.
            2. Check if any times overlap.
            3. Return true if there is a conflict.
            """
            pass    
        
        def process_waitlist(course_id: str) -> str:
            """
            Input: course_id string.
            Output: student_id string of the user popped from the waitlist, or None if the waitlist is empty.
            Procedure:
            1. Find the oldest waitlist entry for the course.
            2. Check if the student can still take the course.
            3. Move student to enrolled status.
            """
            pass
