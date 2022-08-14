from dataclasses import dataclass
from random import random
from numpy.random import beta, normal
from math import pow


@dataclass
class Provider:
    """
    Represents a greedy storage provider. They will attempt to rent-seek, and
    game the system at every possible opportunity.
    """

    balance: float
    capacity: float
    used: float

    # The minimum fee the provider accepts for bids, and the discount they
    # receive on the mkt price of the raw materials (storage)
    mat_price_discount: float

    # Last time the provider received an order, number of timesteps it can go
    # without an order before "going out of business"
    timeout_dir: int
    last_order: int

    # provider id for hashing purpouses
    id: int

    def __hash__(self):
        return self.id

    def __eq__(self, o):
        return self.id == o.id

    def min_fee(self, params, prev_state):
        return (
            (pow(0.5, self.capacity / 953674 + 1) + 0.5)
            * self.mat_price_discount
            * prev_state["mkt_fsprice"]
            / prev_state["mkt_vprice"]
        )


def fund_users(params, substep, state_history, prev_state):
    # Only dole out 0.5% of the treasury, at most, per funding round
    grants = []
    total_doled = 0
    grant_portion = params["grant_portion"] if "grant_portion" in params else 20
    grants_available = min(
        params["grant_max"] if "grant_max" in params else 5,
        grant_portion - (100 - prev_state["providers"][prev_state["treasury"]].balance),
    )

    for u in prev_state["users"].values():
        if total_doled > prev_state["providers"][prev_state["treasury"]].balance:
            break

        if total_doled >= grants_available:
            break

        # This user is not at risk of leaving our platform
        if u.balance != 0:
            continue

        grant = min(
            random() * 0.05 * prev_state["providers"][prev_state["treasury"]].balance,
            grants_available - total_doled,
        )

        grants.append({"user": u, "value": grant})
        total_doled += grant
        grants_available -= grant

    return {"drain_treasury": total_doled, "grants": grants}


def update_provider_capacities(
    params, substep, state_history, prev_state, policy_input
):
    providers = prev_state["providers"]

    for (id, (fs_spent, v_spent)) in policy_input["spent"].items():
        providers[id].used += fs_spent
        providers[id].balance -= v_spent

    return ("providers", providers)


def generate_providers(params, substep, state_history, prev_state):
    """
    Generate new providers, and update the provider ID head according to system
    parameters.
    """

    prev_head = prev_state["provider_head"]
    prev_provs = prev_state["providers"]

    if prev_state["timestep"] % params.get("new_provider_interval", 60) != 0:
        return {"providers": prev_provs, "provider_head": prev_head}

    alpha_sinit_dist, beta_sinit_dist = params.get("provider_init_storage_dist", (5, 5))

    prev_provs[prev_head] = Provider(
        0,
        beta(alpha_sinit_dist, beta_sinit_dist) * 20480,
        0,
        normal(100, params.get("storage_price_discount_dist", 5)) / 100,
        beta(*params.get("provider_responsiveness", [10, 5])) * 100,
        prev_state["timestep"],
        prev_head,
    )

    return {"providers": prev_provs, "provider_head": prev_head + 1}


def register_providers(params, substep, state_history, prev_state, policy_input):
    return ("providers", policy_input["providers"] | prev_state["providers"])


def change_provider_head(params, substep, state_history, prev_state, policy_input):
    return ("provider_head", policy_input["provider_head"])


def resize_prov_sectors(params, substep, state_history, prev_state, policy_input):
    """
    Expands or contracts the provider's available space.

    Depends on whether the provider is ready to reassess its profitability or
    and whether or not it is profitable.
    """
    providers = prev_state["providers"].copy()

    for prov in prev_state["providers"].values():
        if prev_state["timestep"] - prov.last_order < prov.timeout_dir:
            continue

        prov.last_order = prev_state["timestep"]

        # The user must shut down
        if prov.capacity == 0:
            del providers[prov.id]

            continue

        # The user must decrease their capacity
        if prov.capacity - prov.used > 0:
            prov.capacity = prov.used

            continue

        # Increase the producer's capacity by however much space wasn't filled
        # since the last adjustment
        since_history = state_history[prov.last_order : prev_state["timestep"]]
        prov.capacity += max(
            sum(
                sum(o.size for o in state["orders"])
                - sum(prov.capacity for prov in state["providers"].values())
                for state in since_history
            )
            / len(since_history),
            0,
        )

    return ("providers", providers)
