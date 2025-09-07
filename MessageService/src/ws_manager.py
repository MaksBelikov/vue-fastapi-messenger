from collections import defaultdict

import json

from typing import Dict, Set

from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.chat_subscriptions: Dict[int, Set[int]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket):
        self.active_connections[user_id].add(websocket)

    async def disconnect(self, user_id: int, websocket):
        if websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def subscribe_to_chat(self, user_id: int, chat_id: int):
        self.chat_subscriptions[chat_id].add(user_id)

    async def unsubscribe_from_chat(self, user_id: int, chat_id: int):
        if user_id in self.chat_subscriptions[chat_id]:
            self.chat_subscriptions[chat_id].remove(user_id)

    async def broadcast_to_chat(self, chat_id: int, message: dict):
        message_json = json.dumps(message)
        users = self.chat_subscriptions.get(chat_id, set())
        
        for user_id in users:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    try:
                        await websocket.send_text(message_json)
                    except Exception:
                        await self.disconnect(user_id, websocket)

ws_manager = ConnectionManager()