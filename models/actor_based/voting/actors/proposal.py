"""Deals with the creation and management of proposals."""
from dataclasses import dataclass


@dataclass
class Proposal:
    """Represents an proposal."""

    # The total amount of votes needed to pass the proposal.
    # Each token gets translate to some amount of votes based onwhich voting mechanism
    # is used.
    required_votes: float

    # Unique id for the proposal.
    proposal_id: int

    def __init__(self, required_votes, proposal_id):
        """Initialize with the amount of required votes and the proposal id."""
        self.required_votes = required_votes
        self.proposal_id = proposal_id

    def __hash__(self):
        """proposal_id is the hash."""
        return self.proposal_id

    def __eq__(self, o):
        """Equal iff proposal_id's are equal."""
        return self.proposal_id == o.proposal_id
