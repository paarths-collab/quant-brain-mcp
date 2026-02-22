class SessionMemory:

    def __init__(self):
        self.store = {}

    def save(self, session_id, key, data):
        if session_id not in self.store:
            self.store[session_id] = {}
        self.store[session_id][key] = data

    def get(self, session_id, key=None):
        if session_id not in self.store:
            return {}
        
        if key:
            return self.store[session_id].get(key)
            
        return self.store[session_id]
