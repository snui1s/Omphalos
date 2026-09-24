"""Module-level docstring for the sample fixture."""

import functools


@functools.cache
def cached_fn(n: int) -> int:
    """Compute something expensive."""
    return n * 2


class Greeter:
    """Greets people in various languages."""

    def greet(self, name: str) -> str:
        """Return a greeting."""
        return f"Hello, {name}"

    async def fetch_greetings(self):
        pass


def top_level(สวัสดี: str = "ค่ะ") -> str:
    """ฟังก์ชันที่มีชื่อพารามิเตอร์เป็นภาษาไทย."""
    return สวัสดี
