"""
Unit tests for StoneSync Room Admin & Moderation Controls (Module 10)
"""
import asyncio
import json
from server.go_server import Room, RoomManager


class DummyWebSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, payload: str):
        self.sent.append(json.loads(payload))


def _run(coro):
    asyncio.run(coro)

def test_room_host_registration():
    room = Room(room_id="admin-test-room")
    role_host = room.register_player("host_user_1", preferred_color="B")
    assert role_host == "B"
    assert room.host_id == "host_user_1"

    role_p2 = room.register_player("guest_user_2", preferred_color="W")
    assert role_p2 == "W"
    assert room.host_id == "host_user_1"

def test_room_pause_and_winner_adjudication():
    room = Room(room_id="admin-test-room-2")
    room.register_player("host_user_1", preferred_color="B")

    # Test clock pause toggle
    assert not room.is_paused
    room.is_paused = True
    assert room.is_paused

    # Test admin winner adjudication
    assert not room.game.game_over
    room.game.game_over = True
    room.game.winner = "B"
    room.game.win_reason = "adjudication"

    assert room.game.game_over
    assert room.game.winner == "B"
    assert room.game.win_reason == "adjudication"


def test_switch_side_reassigns_players_without_disconnect():
    manager = RoomManager()
    room = manager.get_or_create_room("admin-switch-room")
    ws_host = DummyWebSocket()
    ws_guest = DummyWebSocket()

    room.register_player("host_user_1", preferred_color="B")
    room.register_player("guest_user_2", preferred_color="W")
    room.connections[ws_host] = "host_user_1"
    room.connections[ws_guest] = "guest_user_2"

    _run(manager.handle_message(
        ws_host,
        room,
        "host_user_1",
        json.dumps({"action": "switch_side", "color": "W"})
    ))

    assert room.players["host_user_1"] == "W"
    assert room.players["guest_user_2"] == "B"
    assert ws_host.sent[-1]["your_role"] == "W"
    assert ws_guest.sent[-1]["your_role"] == "B"


def test_kick_player_notifies_target_and_broadcasts_state():
    manager = RoomManager()
    room = manager.get_or_create_room("admin-kick-room")
    ws_host = DummyWebSocket()
    ws_guest = DummyWebSocket()

    room.register_player("host_user_1", preferred_color="B")
    room.register_player("guest_user_2", preferred_color="W")
    room.connections[ws_host] = "host_user_1"
    room.connections[ws_guest] = "guest_user_2"

    _run(manager.handle_message(
        ws_host,
        room,
        "host_user_1",
        json.dumps({"action": "kick_player", "target_player_id": "guest_user_2"})
    ))

    assert "guest_user_2" not in room.players
    assert any(msg.get("type") == "kicked" for msg in ws_guest.sent)
    assert any(
        msg.get("last_action", {}).get("action") == "kick_player"
        for msg in ws_host.sent
    )


def test_reset_action_broadcasts_updated_state():
    manager = RoomManager()
    room = manager.get_or_create_room("admin-reset-room")
    ws_host = DummyWebSocket()
    ws_guest = DummyWebSocket()

    room.register_player("host_user_1", preferred_color="B")
    room.register_player("guest_user_2", preferred_color="W")
    room.connections[ws_host] = "host_user_1"
    room.connections[ws_guest] = "guest_user_2"

    _run(manager.handle_message(
        ws_host,
        room,
        "host_user_1",
        json.dumps({"action": "reset", "board_size": 13, "komi": 6.5, "handicap": 0})
    ))

    assert room.game.board_size == 13
    assert any(
        msg.get("last_action", {}).get("action") == "reset"
        for msg in ws_host.sent
    )
    assert ws_guest.sent[-1]["game_state"]["board_size"] == 13

