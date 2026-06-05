from typing import Dict, List


class SessionContext:
    def __init__(self) -> None:
        self.history: Dict[int, List[str]] = {}

    def append(self, user_id: int, message: str) -> None:
        self.history.setdefault(user_id, []).append(message)

    def get(self, user_id: int) -> List[str]:
        return self.history.get(user_id, [])

    def clear(self, user_id: int) -> None:
        self.history.pop(user_id, None)
