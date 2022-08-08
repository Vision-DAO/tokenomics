"""Deals with the creation and management of users."""
from dataclasses import dataclass


@dataclass
class User:
    """
    Represents a user.

    Can create proposals, vote on proposals, and buy tokens.
    """

    # represents a balance of interchangable currency (not in idea tokens)
    balance: float

    user_id: int

    # dict of token_id -> amount
    tokens: {}

    def __init__(self, balance, user_id):
        """Take the user's initial balance, and the user's ID."""
        self.balance = balance
        self.tokens = {}
        self.user_id = user_id

    def __hash__(self):
        """user_id is the hash."""
        return self.user_id

    def __eq__(self, o):
        """Equal iff user_id's are equal."""
        return self.user_id == o.user_id


def generate_users(params, substep, state_history, prev_state, policy_input):
    """Add a new user every 3 weeks."""
    prev_users = prev_state["users"]
    if substep % 30 != 0:
        return ("users", prev_users)

    return ("users", [*prev_users, User(100, len(prev_users))])
