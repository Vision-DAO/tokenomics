"""Implements methods for creating, and managing the buyer actor."""

import random
from dataclasses import dataclass
from numpy.random import normal, beta
from math import ceil


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

    # The # of Vision tokens that the user has won in challenges
    challenges_won: float

    # How often and how much of their portfolio this user sells
    sell_interval: float
    sell_pct: float

    # buyer id for hashing purpouses
    id: int

    def __hash__(self):
        return self.id

    def __eq__(self, o):
        return self.id == o.id


def update_funded_balances(params, substep, state_history, prev_state, policy_input):
    users = prev_state["users"]

    for grant in policy_input["grants"]:
        users[grant["user"].id].balance += grant["value"]

    return ("users", users)


def generate_users(params, substep, state_history, prev_state):
    # Add a new user for every user every 3 weeks
    prev_users = prev_state["users"]
    new_user_rate = params["new_user_interval"] if "new_user_interval" in params else 10

    if prev_state["timestep"] % new_user_rate != 0:
        return {"user_head": prev_state["user_head"], "users": prev_users}

    (alpha_reneg, beta_reneg) = (
        params["user_timeout_dist"] if "user_timeout_dist" in params else [2, 15]
    )

    return {
        "user_head": prev_state["user_head"] * 2,
        "users": prev_users
        | {
            (i + prev_state["user_head"]): Buyer(
                0,
                normal(*params.get("user_stinginess_dist", (0, 5))),
                prev_state["timestep"],
                0,
                0,
                beta(alpha_reneg, beta_reneg),
                0,
                ceil(normal(*params.get("profit_taking_interval", [200, 50]))),
                beta(*params.get("profit_taking_amt_dist", [1, 5])),
                i + prev_state["user_head"],
            )
            for i in range(len(prev_state["users"]))
        },
    }


def register_users(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])


def change_user_head(params, substep, state_history, prev_state, policy_input):
    return ("user_head", policy_input["user_head"])


def register_orders(params, substep, state_history, prev_state, policy_input):
    return (
        "orders",
        [*prev_state["orders"], *[o for o in policy_input.values() if o is not None]],
    )


def update_user_balances(params, substep, state_history, prev_state, policy_input):
    users = prev_state["users"]

    for (buyer, o) in policy_input.items():
        if o is None:
            continue

        users[o.buyer].all_orders += 1
        users[o.buyer].balance -= o.price * o.size

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

    # Number of VIS a provider needs to match of a buyer's bid to accept it
    col_rate = params.get("collateralization_rate", 1.0)

    for prov in prev_state["providers"].values():
        mine = [o for o in order_options if o not in signal["filled"]]

        # Choose the most profitable options to fill up our
        eligible = [x for x in mine if x.price >= prov.min_fee(params, prev_state)]

        # Sort in ascending order to remove least profitable options
        best = sorted(eligible, key=lambda x: x.price * x.size)

        taken = best
        used = sum(x.size for x in best)

        # The provider must stake collateral = 100% of the value of the contract
        balance_used = sum(col_rate * x.size * x.price for x in best)

        # Remove the last profitable options that are above our capacity
        while (
            used + prov.used > prov.capacity
            or prov.balance - balance_used < 0
            and len(taken) > 0
        ):
            freed = taken.pop()
            used -= freed.size
            balance_used -= col_rate * freed.size * freed.price

        # Use the determined price to fill all of the orders, and remove the
        # specified units from the provider
        signal = {
            "filled": {**{order: prov for order in taken}, **signal["filled"]},
            "spent": {
                prov.id: (used, balance_used),
                **signal["spent"],
            },
        }

    return signal


def update_last_contract(params, substep, state_history, prev_state, policy_input):
    users = prev_state["users"]

    new_idea_int = params["new_idea_interval"] if "new_idea_interval" in params else 30

    for u in users.values():
        if prev_state["timestep"] - u.last_contract == new_idea_int:
            u.last_contract = prev_state["timestep"]

    return ("users", users)


def orphan_bored_users(params, substep, state_history, prev_state, policy_input):
    users = {}

    # Remove spent balances from users, and kill ones that have gone too long
    # without an accepted order
    for u in prev_state["users"].values():
        canceled = policy_input["user_counts"].get(u.id, 0)
        u.unfilled_orders += canceled

        spent = policy_input["user_balances"].get(u.id, 0)
        u.balance -= spent

        if u.all_orders == 0 or u.unfilled_orders / u.all_orders <= u.ux_tolerance:
            users[u.id] = u

    return ("users", users)
