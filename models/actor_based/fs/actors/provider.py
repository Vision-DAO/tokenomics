from dataclasses import dataclass
from random import random


@dataclass
class Provider:
    """
    Represents a greedy storage provider. They will attempt to rent-seek, and
    game the system at every possible opportunity.
    """

    balance: float
    capacity: float
    used: float

    # The minimum fee the provider accepts for bids
    min_fee: float

    # provider id for hashing purpouses
    id: int

    def __hash__(self):
        return self.id

    def __eq__(self, o):
        return self.id == o.id


def fund_users(params, substep, state_history, prev_state):
    # Only dole out 0.5% of the treasury, at most, to each unfunded user
    grants = []
    total_doled = 0

    for u in prev_state["users"]:
        if total_doled > prev_state["treasury"].balance:
            break

        # This user is at risk of leaving our platform. Give them some money
        if u.balance == 0:
            grant = random() * 0.05 * prev_state["treasury"].balance

            grants.append({"user": u, "value": grant})
            total_doled += grant

    return {"drain_treasury": total_doled, "grants": grants}


def update_provider_capacities(
    params, substep, state_history, prev_state, policy_input
):
    providers = prev_state["providers"]

    for prov in providers:
        if prov not in policy_input["spent"]:
            continue

        prov.used += policy_input["spent"][prov]

    return ("providers", providers)
