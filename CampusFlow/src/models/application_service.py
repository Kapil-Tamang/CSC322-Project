class ApplicationService:
    """
    Manages key application services.
    """
    
    def submit_application(visitor_id: str, requested_role: str, academic_data: dict) -> str:
        """
        Input: visitor_id string, requested_role string ('Student' or 'Instructor'), academic_data dictionary (containing GPA history, transcripts, or department requests).
        Output: app_id string of the newly generated application.
        Procedure:
        1. Check if visitor exists.
        2. Create pending application with data.
        3. Return application ID.
        """
        pass
    
    def evaluate_application(registrar_id: str, app_id: str, decision: str, notes: str) -> bool:
        """
        Input: registrar_id string, app_id string, decision string ('Approve' or 'Reject'), notes string if decided to reject.
        Output: Boolean indicating transaction success.
        Procedure:
        1. Verify registrar privileges.
        2. If approved, create new Student or Instructor role and update status.
        3. If rejected, mark application as rejected.
        4. Save registrar notes and resolution date.
        """
        pass
