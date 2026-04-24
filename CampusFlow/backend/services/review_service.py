class ReviewService:
    """
    Manages the submission of course evaluations and performs content moderation.
    """

    def submit_review(student_id: str, course_id: str, rating: int, text: str) -> bool:
        """
        Input: student_id string, course_id string, rating integer (1-5), text string.
        Output: Boolean indicating successful submission.
        """
        pass 

   def filter_inappropriate_content(text: str) -> bool:
        """
        Input: raw review text string.
        Output: Boolean True if inappropriate content is detected, False otherwise.
        """
        pass 
