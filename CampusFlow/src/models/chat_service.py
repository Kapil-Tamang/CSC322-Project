class ChatService:
    """
    Provides conversational AI assistance utilizing a local knowledge base.
    """
    
    def process_query(user_id: str, role: str, query: str, session_id: str) -> str:
        """
        Input: user_id string, role string, query string, session_id string.
        Output: AI Response string.
        Procedure:
        1. Search local knowledge base based on user role.
        2. If local answer is found, return it.
        3. If not, use external AI and add hallucination warning.
        4. Save chat history.
        """
        pass
    
    def retrieve_from_local_kb(query: str, scope_filter: dict) -> str:
        """
        Input: query string, scope_filter dictionary.
        Output: Extracted textual context string.
        Procedure:
        1. Convert query to vector.
        2. Find matching documents in local database.
        3. Return matching text.
        """
        pass
