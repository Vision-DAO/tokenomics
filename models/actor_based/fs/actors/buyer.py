"""Implements methods for creating, and managing the buyer actor."""

import random
from dataclasses import dataclass
from numpy.random import normal, beta


@dataclass
class Buyer:
    """Represents a Vision user that wants to pay for storage."""

    balance: float

    # How much of a premium this user is willing to pay for the ability to store
    # files, compared to the going market rate.
    stinginess: float

    # The time at which the user last had an idea, and got a contract for it
    last_contract: int

    # How many orders were timed-out due to not enough suppliers
    unfilled_orders: int

    # How many orders were created
    all_orders: int

    # The % of orders that the user can tolerate not getting filled, or being
    # reneged upon
    ux_tolerance: float

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

    (alpha_reneg, beta_reneg) = (
        params["user_timeout_dist"] if "user_timeout_dist" in params else [2, 15]
    )

    return (
        "users",
        [
            *prev_users,
            *[
                Buyer(
                    0,
                    normal(0, 0.5),
                    prev_state["timestep"],
                    0,
                    0,
                    beta(alpha_reneg, beta_reneg),
                    i,
                )
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
    for (buyer, o) in policy_input.items():
        if o is None:
            continue

        o.buyer.all_orders += 1
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


def orphan_bored_users(params, substep, state_history, prev_state, policy_input):
    users = []

    # Remove spent balances from users, and kill ones that have gone too long
    # without an accepted order
    for u in prev_state["users"]:
        canceled = policy_input["user_counts"].get(u, 0)
        u.unfilled_orders += canceled

        spent = policy_input["user_balances"].get(u, 0)
        u.balance -= spent

        print(u.all_orders, u.unfilled_orders, u.ux_tolerance)

        if u.all_orders == 0 or u.unfilled_orders / u.all_orders < u.ux_tolerance:
            users.append(u)

    return ("users", users)
