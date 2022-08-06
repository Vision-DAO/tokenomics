"""Implements methods for creating, and managing the buyer actor."""

from . contract import Contract
import random
from dataclasses import dataclass

@dataclass
class Buyer:
    """Represents a Vision user that wants to pay for storage."""

    balance: float
    contracts: list[Contract]

    # How much of a premium this user is willing to pay for the ability to store
    # files, compared to the going market rate.
    stinginess: float

    # The time at which the user last had an idea, and got a contract for it
    last_contract: int


def update_funded_balances(params, substep, state_history, prev_state, policy_input):
    for grant in policy_input.grants:
        grant["user"].balance += grant["value"]

    return ("users", prev_state["users"])


def generate_users(params, substep, state_history, prev_state, policy_input):
    # Add a new user every 3 weeks
    if substep % 30 != 0:
        return ("users", prev_state["users"])

    return ("users", [*prev_state["users"], Buyer(0, [], substep)])


def generate_orders(params, substep, state_history, prev_state, policy_input):
    # Users get ideas every 10 steps (approximately once every week)
    orders = [Contract(None, buyer, -1, prev_state["mkt_sprice"])
              for buyer in prev_state["users"]
              if prev_state["timestep"] == buyer.last_contract]

    return ("orders", [*prev_state["orders"], *orders])


def negotiate_orders(params, substep, state_history, prev_state):
    # Divy up the orders by simulating network latency, giving 3 orders to each
    # provider, which they may or may not be able to fulfill. Pick the biggest
    # of them in the round, and then re-run next round
    order_options = list(range(len(prev_state["orders"])))
    random.shuffle(order_options)

    # The units of capacity the providers spent, the list of orders that were
    # filled, and the prices they were filled at
    signal = {
        "filled": {},
        "spent": {},
    }

    for prov in prev_state["providers"]:
        mine = order_options[:3]
        order_options = order_options[3:] if len(order_options) > 3 else []

        # Choose the most profitable options to fill up our
        eligible = [x for x in mine if x.price < prov.min_fee]
        best = sorted(eligible, key=lambda x: x.price)

        taken = best
        used = prov.used

        # Remove the last profitable options that are above our capacity
        while used > prov.capacity and len(taken) > 0:
            freed = taken.pop()
            used -= freed.size

        # Use the determined price to fill all of the orders, and remove the
        # specified units from the provider
        signal = {
            "filled": {
                **{order: order.price for order in taken},
                **signal["filled"]
            },
            "spent": {
                prov: used,
                **signal["spent"],
            }
        }

    return signal


def update_last_contract(params, substep, state_history, prev_state, policy_input):
    users = prev_state["users"]

    for u in users:
        if prev_state["timestep"] - u.last_contract == 10:
            u.last_contract = prev_state["timestep"]

    return users
