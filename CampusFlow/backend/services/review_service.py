class ReviewService:
    """
    Manages the submission of course evaluations and performs content moderation.
    """
    
    def submit_review(student_id: str, course_id: str, rating: int, text: str) -> bool:
        """
        Input: student_id string, course_id string, rating integer (1-5), text string.
        Output: Boolean indicating successful submission.
        Procedure:
        1. Verify student completed the course.
        2. Check text for bad words.
        3. If bad words found, flag and hide review.
        4. Otherwise, save and update course rating.
        """
        pass 
    
    def filter_inappropriate_content(text: str) -> bool:
        """
        Input: raw review text string.
        Output: Boolean True if inappropriate content is detected, False otherwise.
        Procedure:
        1. Compare text against banned words list.
        2. Return true if bad words are found.
        """
        pass 
