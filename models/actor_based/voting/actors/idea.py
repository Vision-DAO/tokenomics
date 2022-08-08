"""Deals with the creation and management of ideas."""
from dataclasses import dataclass


@dataclass
class Idea:
    """
    Represents an idea.

    Supports the creation of proposals and selling of its tokens.
    """

    # The total amount of the idea's token in circulation
    # For now, all tokens are worth the same
    volume: float

    # Unique id for the idea's token
    token_id: int

    # The amount of tokens owned by the idea and not shareholders
    treasury: float
    shareholders: []

    def __init__(self, volume, token_id):
        """Take the volume of the idea's token, and the token ID."""
        self.volume = volume
        self.treasury = volume
        self.shareholders = []
        self.token_id = token_id

    def __hash__(self):
        """token_id is the hash."""
        return self.token_id

    def __eq__(self, o):
        """Equal iff token_id's are equal."""
        return self.token_id == o.token_id
