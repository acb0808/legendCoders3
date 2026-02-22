from typing import Dict, List
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {} # arena_id: [websocket_client1, websocket_client2]

    async def connect(self, arena_id: str, websocket: WebSocket):
        if arena_id not in self.active_connections:
            self.active_connections[arena_id] = []
        self.active_connections[arena_id].append(websocket)

    def disconnect(self, arena_id: str, websocket: WebSocket):
        if arena_id in self.active_connections:
            try:
                self.active_connections[arena_id].remove(websocket)
            except ValueError:
                # Connection already removed, ignore
                pass
            
            if not self.active_connections[arena_id]:
                del self.active_connections[arena_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")

    async def broadcast_to_room(self, arena_id: str, message: str):
        if arena_id in self.active_connections:
            stale_connections = []
            for connection in self.active_connections[arena_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error broadcasting to connection in room {arena_id}: {e}")
                    stale_connections.append(connection)
            
            # Clean up stale connections found during broadcast
            for stale in stale_connections:
                try:
                    self.active_connections[arena_id].remove(stale)
                except ValueError:
                    pass
            
            if not self.active_connections[arena_id]:
                del self.active_connections[arena_id]

# Global manager instance
manager = ConnectionManager()
