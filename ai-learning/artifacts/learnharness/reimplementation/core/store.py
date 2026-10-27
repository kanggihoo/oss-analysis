"""In-memory ChatStore port (getChat / saveMessages / saveTree). Test double, not spec'd."""


class ChatStore:
    def __init__(self):
        self.chats = {}

    def create_chat(self, chat_id, messages=None, tree=None, kind=None):
        self.chats[chat_id] = {"id": chat_id, "messages": list(messages or []), "tree": tree,
                               "updatedAt": None, "kind": kind}

    def get_chat(self, chat_id):
        return self.chats.get(chat_id)

    def save_messages(self, chat_id, messages):
        rec = self.get_chat(chat_id)
        if rec is None:
            raise KeyError(f"Chat not found: {chat_id}")
        rec["messages"] = list(messages)
        rec["updatedAt"] = "bumped"  # saveMessages bumping updatedAt is a guess (C-07 only says saveTree does not)

    def save_tree(self, chat_id, tree):
        rec = self.get_chat(chat_id)
        if rec is None:
            raise KeyError(f"Chat not found: {chat_id}")
        rec["tree"] = tree  # deliberately does not touch updatedAt
