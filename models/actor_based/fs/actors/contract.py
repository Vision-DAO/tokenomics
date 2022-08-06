from . provider import Provider
from . buyer import Buyer
from dataclasses import dataclass


@dataclass
class Contract:
    """Represent an agreement between a storage provider and user."""

    provider: Provider
    buyer: Buyer
    size: float
    next_epoch: int
    epoch_created_at: int
    price: float


def update_treasury_balance(params, substep, state_history, prev_state, policy_input):
    prev_state["treasury"].balance -= policy_input.total_doled

    return ("treasury", prev_state["treasury"])
