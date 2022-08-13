"""Manages voting events."""
from dataclasses import dataclass
from actors.user import User


@dataclass
class Voting_event:
    """
    Represents a voting event.

    Catalogues the results of the enforcer-jury mechanism.
    """

    # true if enforcer claimed guilty
    # (and thus the voting event went through the enforcer-jury mechanism)
    # if false, there was no valid enforcer or no enforcer contested
    enforcer: User
    jury: [User]
    jury_verdict_guilty: bool
    real_result_guilty: bool

    # the amount of tokens the voter voted with that may or may not be lost based on
    # the jury's verdict
    voter_tokens: float

    voting_event_id: int

    def __init__(self):
        """Init with assumption of not guilty."""
        self.enforcer = None
        self.jury = []
        self.jury_verdict_guilty = False
        self.real_result_guilty = False
        self.voter_tokens = 0
        self.voting_event_id = -1

    def __hash__(self):
        """voting_event_id is the hash."""
        return self.voting_event_id

    def __eq__(self, o):
        """Equal iff voting_event_id's are equal."""
        return self.voting_event_id == o.voting_event_id


def process_voting_events(params, substep, state_history, prev_state, policy_input):
    """Create the voting events from votes made in the substep."""
    new_events = []
    event: Voting_event
    for event in policy_input["voting_events"]:
        event.voting_event_id = len(policy_input["voting_events"]) + len(new_events)
        new_events.append(event)

    return ("voting_events", [*prev_state["voting_events"], *new_events])
