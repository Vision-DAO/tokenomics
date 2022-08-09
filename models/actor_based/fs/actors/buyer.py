"""Implements methods for creating, and managing the buyer actor."""

import random
from dataclasses import dataclass
from numpy.random import normal
from math import floor


@dataclass
class Buyer:
    """Represents a Vision user that wants to pay for storage."""

    balance: float

    # How much of a premium this user is willing to pay for the ability to store
    # files, compared to the going market rate.
    stinginess: float

    # The time at which the user last had an idea, and got a contract for it
    last_contract: int

    # buyer id for hashing purpouses
    id: int

    def __hash__(self):
        return self.id

    def __eq__(self, o):
        return self.id == o.id


def update_funded_balances(params, substep, state_history, prev_state, policy_input):
    for grant in policy_input["grants"]:
        grant["user"].balance += grant["value"]

    return ("users", prev_state["users"])


def generate_users(params, substep, state_history, prev_state, policy_input):
    # Add a new user for every user every 3 weeks
    prev_users = prev_state["users"]
    new_user_rate = params["new_user_interval"] if "new_user_interval" in params else 10

    if prev_state["timestep"] % new_user_rate != 0:
        return ("users", prev_users)

    return (
        "users",
        [
            *prev_users,
            *[
                Buyer(0, floor(normal(0, 0.5)), prev_state["timestep"], i)
                for i in range(len(prev_state["users"]), 2 * len(prev_state["users"]))
            ],
        ],
    )


def register_orders(params, substep, state_history, prev_state, policy_input):
    return (
        "orders",
        [*prev_state["orders"], *[o for o in policy_input.values() if o is not None]],
    )


def update_user_balances(params, substep, state_history, prev_state, policy_input):
    if "filled" in policy_input:
        for o in policy_input["filled"]:
            o.buyer.balance -= o.price * o.size

    return ("users", prev_state["users"])


def negotiate_orders(params, substep, state_history, prev_state):
    # Divy up the orders by simulating network latency, giving 20 orders to each
    # provider, which they may or may not be able to fulfill. Pick the biggest
    # of them in the round, and then re-run next round
    order_options = list(range(len(prev_state["orders"])))
    random.shuffle(order_options)
    order_options = [prev_state["orders"][i] for i in order_options]

    # The units of capacity the providers spent, the list of orders that were
    # filled, and the prices they were filled at
    signal = {
        "filled": {},
        "spent": {},
    }

    for prov in prev_state["providers"]:
        mine = order_options[:]
        order_options = order_options[3:] if len(order_options) > 20 else []

        # Choose the most profitable options to fill up our
        eligible = [x for x in mine if x.price >= prov.min_fee]

        # Sort in ascending order to remove least profitable options
        best = sorted(eligible, key=lambda x: x.price * x.size)

        taken = best
        used = sum(x.size for x in best)

        # Remove the last profitable options that are above our capacity
        while used + prov.used > prov.capacity and len(taken) > 0:
            freed = taken.pop()
            used -= freed.size

        # Use the determined price to fill all of the orders, and remove the
        # specified units from the provider
        signal = {
            "filled": {**{order: prov for order in taken}, **signal["filled"]},
            "spent": {
                prov: used,
                **signal["spent"],
            },
        }

    return signal


def update_last_contract(params, substep, state_history, prev_state, policy_input):
    users = prev_state["users"]

    new_idea_int = params["new_idea_interval"] if "new_idea_interval" in params else 30

    for u in users:
        if prev_state["timestep"] - u.last_contract == new_idea_int:
            u.last_contract = prev_state["timestep"]

    return ("users", users)
