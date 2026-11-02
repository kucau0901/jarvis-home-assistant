"""When to send what changed: the timing, kept apart from Home Assistant so it can be tested alone.

Urgent changes (a door, a lock, a leak, the alarm, someone coming or going: Jarvis says which) go within
URGENT_DELAY seconds; the rest wait for the next batch, at most one every GAP seconds. Every request counts
towards the token's day in Jarvis (500 by default), so a busy house of lights and motion sensors must not send
each change on its own.

Within a batch, an entity is sent once, as its first "from" and latest "to"; one that changed and changed back
is not sent at all. A batch that fails is put back, behind anything newer for the same entity, and the next try
waits, doubling up to MAX_BACKOFF.
"""

from __future__ import annotations

GAP = 300.0
URGENT_DELAY = 2.0
MAX_BATCH = 100
FIRST_BACKOFF = 30.0
MAX_BACKOFF = 900.0


class Batcher:
    """Changes waiting to be sent, and when they are due. Times are seconds on any one clock (monotonic)."""

    def __init__(self, gap: float = GAP, urgent_delay: float = URGENT_DELAY, max_batch: int = MAX_BATCH) -> None:
        self._gap = gap
        self._urgent_delay = urgent_delay
        self._max = max_batch
        self._pending: dict[str, tuple[str, str]] = {}
        self._urgent_at: float | None = None
        self._last_sent = float("-inf")
        self._retry_at = float("-inf")
        self._backoff = 0.0

    def add(self, entity: str, old: str, new: str, urgent: bool, now: float) -> None:
        """A change seen: kept as the first state it left and the latest it reached."""
        first = self._pending[entity][0] if entity in self._pending else old
        self._pending[entity] = (first, new)
        if urgent:
            at = now + self._urgent_delay
            self._urgent_at = at if self._urgent_at is None else min(self._urgent_at, at)

    def due(self, now: float) -> bool:
        """Whether to send now: something waits, no failure is being waited out, and it is urgent or the gap has passed."""
        if not self._pending or now < self._retry_at:
            return False
        if self._urgent_at is not None and now >= self._urgent_at:
            return True
        return now - self._last_sent >= self._gap

    def take(self, now: float) -> list[dict[str, str]]:
        """What to send, as Jarvis takes it ({id, from, to}); what changed back is dropped."""
        out: list[dict[str, str]] = []
        for entity in list(self._pending)[: self._max]:
            old, new = self._pending.pop(entity)
            if old != new:
                out.append({"id": entity, "from": old, "to": new})
        self._last_sent = now
        self._urgent_at = None if not self._pending else self._urgent_at
        return out

    def failed(self, sent: list[dict[str, str]], now: float) -> None:
        """A batch did not reach Jarvis: put back what nothing newer has replaced, and wait before the next try."""
        for c in sent:
            if c["id"] not in self._pending:
                self._pending[c["id"]] = (c["from"], c["to"])
        self._backoff = min(MAX_BACKOFF, self._backoff * 2 if self._backoff else FIRST_BACKOFF)
        self._retry_at = now + self._backoff

    def succeeded(self) -> None:
        self._backoff = 0.0
        self._retry_at = float("-inf")

    def waiting(self) -> int:
        return len(self._pending)
