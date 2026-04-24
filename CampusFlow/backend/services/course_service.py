class CourseService:
    """
    Handles the course lifecycle, including instructor assignment and course catalog management.
    """

    def create_course(registrar_id: str, course_data: dict) -> str:
        """
        Input: registrar_id string, course_data dictionary (containing Title, Description, Credits, Capacity, Schedule, Department).
        Output: course_id string.
       Procedure:
        1. Verify registrar privileges.
        2. Validate course details.
        3. Save new course to database.
        4. Return course ID.
        """
        pass

   def assign_instructor(registrar_id: str, course_id: str, instructor_id: str) -> bool:
        """
        Input: registrar_id string, course_id string, instructor_id string.
        Output: Boolean indicating successful assignment.
       Procedure:
        1. Verify registrar privileges.
        2. Check if instructor exists.
        3. Link instructor to course.
        """
        pass
   def update_course_availability(registrar_id: str, course_id: str, phase: str) -> bool:
        """
        Input: registrar_id string, course_id string, phase string ('Registration', 'Active', 'Grading', 'Closed').
        Output: Boolean indicating successful phase transition.
       Procedure:
        1. Verify registrar privileges.
        2. Update course phase (e.g., to 'Registration' or 'Active').
        """
        pass

    def browse_courses(filters: dict) -> list:
        """
        Input: filters dictionary (optional keys: Department, Instructor, Availability, Keyword).
        Output: List of detailed course dictionary objects.
        Procedure:
        1. Search courses using filters.
        2. Fetch ratings and enrollments.
        3. Return formatted list of courses.
        """
        pass        
