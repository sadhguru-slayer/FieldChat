class RedisKeys:
    """
    ========
    Users
    ========
    """
    @staticmethod
    def user_chanel(user_id:str)->str:
        return f"user:{user_id}"

    @staticmethod
    def user_connections(user_id:str)->str:
        return f"user:{user_id}:connections"

    """ 
        ==============
        Conversations
        ==============    
    """
    @staticmethod
    def conversation_key(conversation_id:str):
        return f"conversation:{conversation_id}"

    # To get the user's conversation
    @staticmethod
    def user_conversations(user_id:str)->str:
        return f"user:{user_id}:conversations"

    # To get the users in a conversation
    @staticmethod
    def conversation_members(conv_id:str)->str:
        return f"conversation:{conv_id}:members"

    """
    ========
    Presence
    ========
    """

    @staticmethod
    def presence_watchers(user_id:str)->str:
        return f"presense_watchers:{user_id}"

    @staticmethod
    def online_users()->str:
        return f"online_users"