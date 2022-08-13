"""Deals with the creation and management of ideas."""
from dataclasses import dataclass
from random import random
import math


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
    idea_id: int

    # The amount of tokens owned by the idea and not shareholders
    treasury: float

    # Set of all users by user_id
    shareholders: {}

    def __init__(self, volume, idea_id):
        """Take the volume of the idea's token, and the token ID."""
        self.volume = volume
        self.treasury = volume
        self.shareholders = set()
        self.idea_id = idea_id

    def __hash__(self):
        """idea_id is the hash."""
        return self.idea_id

    def __eq__(self, o):
        """Equal iff idea_id's are equal."""
        return self.idea_id == o.idea_id


def generate_ideas(params, substep, state_history, prev_state, policy_input):
    """Add a new user every 45 ticks."""
    prev_ideas = prev_state["ideas"]

    if prev_state["timestep"] % 45 != 0:
        return ("ideas", prev_ideas)

    return (
        "ideas",
        [*prev_ideas, Idea(10 * math.floor(random() * 100), len(prev_ideas))],
    )


def process_token_sell(params, substep, state_history, prev_state, policy_input):
    """Process the token sell on the ideas' side."""
    idea: Idea
    for idea in prev_state["ideas"]:
        if idea.idea_id in policy_input["idea_treasury"]:
            idea.treasury = policy_input["idea_treasury"][idea.idea_id]

        if idea.idea_id in policy_input["idea_new_shareholders"]:
            idea.shareholders.update(
                policy_input["idea_new_shareholders"][idea.idea_id]
            )

    return ("ideas", prev_state["ideas"])
