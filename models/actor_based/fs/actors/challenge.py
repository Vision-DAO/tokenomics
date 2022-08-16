"""Implements wrappers and tokenomics for proof of storage challenges."""
from dataclasses import dataclass
from random import randrange, shuffle
from math import ceil


@dataclass
class Challenge:
    """Represents a proof of storage challenge due by a certain timestep."""

    # ID of the user that created the challenge
    enforcer: int

    # ID of the order being challenged
    order: int

    # When the provider needs to give a proof by
    due_by: int

    # Whether or not the provider submitted a valid proof
    proof_submitted: bool


def create_challenges(params, substep, state_history, prev_state):
    """Update the challenge head, and creates new challenges for orders."""
    users = prev_state["users"]
    challenges = prev_state["challenges"]
    orders = prev_state["active"]

    gas = prev_state["mkt_gprice"] / prev_state["mkt_vprice"]

    # Find users who have enough VIS to cover gas costs
    eligible = list(
        filter(
            lambda u: u.balance >= gas,
            users.values(),
        )
    )

    for o in orders:
        # Skip orders that already have an active challenge
        if o.id in prev_state["challenges"]:
            continue

        # The order is not yet eligible for a challenge
        if prev_state["timestep"] < o.next_challenge:
            continue

        if (
            o.challenges_left <= 0
            or prev_state["timestep"] - o.epoch_created_at >= o.next_epoch
        ):
            continue

        # Allow the user who has the greatest expected outcome from challenging
        # the storage provider to ask for a proof
        n_inform = ceil(params.get("challenge_awareness_rate", 0.1) * len(users))

        # See analysis.org. Select only a few users to know about the challenge
        # being ready
        aware = eligible[:n_inform]
        shuffle(aware)

        if len(aware) == 0:
            continue

        # And then find the most fit for the opportunity
        takes_action = sorted(aware, key=lambda u: u.challenges_won, reverse=True)[0]

        # Pay the gas
        takes_action.balance -= gas
        takes_action.challenges_won -= gas

        # Set the next challenge to the found date
        next_challenge = (
            randrange(prev_state["timestep"] - o.epoch_created_at, o.next_epoch)
            + o.epoch_created_at
        )
        o.next_challenge = next_challenge
        o.challenges_left -= 1

        # Remove the user if they no longer have enough balance
        if takes_action.balance < prev_state["mkt_gprice"] / prev_state["mkt_vprice"]:
            eligible.remove(takes_action)

        users[takes_action.id] = takes_action
        challenges[o.id] = Challenge(
            takes_action.id,
            o.id,
            next_challenge,
            False,
        )

    return {"users": users, "challenges": challenges, "active": orders}


def spend_challenge_gas(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])


def register_challenges(params, substep, state_history, prev_state, policy_input):
    return ("challenges", policy_input["challenges"])


def update_challenge_counters(params, substep, state_history, prev_state, policy_input):
    return ("active", policy_input["active"])


def answer_challenges(params, substep, state_history, prev_state):
    storage_stolen = prev_state["storage_stolen"]
    providers = prev_state["providers"]
    users = prev_state["users"]
    challenges = prev_state["challenges"]
    active = prev_state["active"]
    slashed = prev_state["v_slashed"]
    burned = prev_state["v_burned"]

    for i, order in enumerate(prev_state["active"]):
        epoch_size = 1 / (order.next_epoch - order.epoch_created_at)
        order_cost = (
            providers[order.provider].min_fee(params, prev_state)
            * order.size
            * epoch_size
        )
        reaped = order.size * order.price

        # Cheat if it has worked so far, within our limits
        if (
            providers[order.provider].forges_won
            > providers[order.provider].risk_tolerance
            * providers[order.provider].balance
        ):
            # We lost this time
            if order.id in prev_state["challenges"]:
                challenge = prev_state["challenges"][order.id]

                # Distribute according to params, and google doc
                # (burning implicit when initial stake cast)
                users[challenge.enforcer].challenges_won += reaped * params.get(
                    "slashing_dist_enf", 0.5
                )
                providers[prev_state["treasury"]].balance += params.get(
                    "slashing_dist_dao", 0.25
                )

                # Record statistics
                slashed += reaped
                burned += reaped * (
                    1
                    - (
                        params.get("slashing_dist_enf", 0.5)
                        + params.get("slashing_dist_dao", 0.25)
                    )
                )

                # Return remaining fee paid
                users[order.buyer].balance += reaped

                # Kill contract, and kill challenge
                del challenges[order.id]
                providers[order.provider].used -= order.size
                active[i] = None

                continue

            # We won
            storage_stolen += order.size
            providers[order.provider].forges_won += order_cost

            continue

        # Enforcer lost
        if order.id in prev_state["challenges"]:
            challenge = prev_state["challenges"][order.id]

            # Remove the challenge
            del challenges[order.id]

    return {
        "storage_stolen": storage_stolen,
        "providers": providers,
        "users": users,
        "challenges": challenges,
        "active": list(filter(lambda x: x is not None, active)),
        "v_slashed": slashed,
        "v_burned": burned,
    }


def steal_storage(params, substep, state_history, prev_state, policy_input):
    return ("storage_stolen", policy_input["storage_stolen"])


def slash_providers(params, substep, state_history, prev_state, policy_input):
    return ("providers", policy_input["providers"])


def reward_enforcers(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])


def kill_challenges(params, substep, state_history, prev_state, policy_input):
    return ("challenges", policy_input["challenges"])


def remove_slashed_orders(params, substep, state_history, prev_state, policy_input):
    return ("active", policy_input["active"])


def slash_supply(params, substep, state_history, prev_state, policy_input):
    return ("v_slashed", policy_input["v_slashed"])


def burn_supply(params, substep, state_history, prev_state, policy_input):
    return ("v_burned", policy_input["v_burned"])
