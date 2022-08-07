"""Implements methods for creating, and interacting with contracts."""

from .provider import Provider
from .buyer import Buyer
from numpy.random import beta
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

    id: int

    def __hash__(self):
        return self.id

    def __eq__(self, o):
        return self.id == o.id


def update_treasury_balance(params, substep, state_history, prev_state, policy_input):
    prev_state["treasury"].balance -= policy_input["drain_treasury"]

    return ("treasury", prev_state["treasury"])


def remove_fulfilled_orders(params, substep, state_history, prev_state, policy_input):
    return (
        "orders",
        [o for o in prev_state["orders"] if o not in policy_input["filled"]],
    )


def add_fulfilled_orders(params, substep, state_history, prev_state, policy_input):
    return (
        "active",
        [
            Contract(
                prov,
                order.buyer,
                order.size,
                prev_state["timestep"] + 1,
                order.epoch_created_at,
                order.price,
                len(prev_state["active"]),
            )
            for (order, prov) in policy_input["filled"]
        ],
    )


def generate_orders(params, substep, state_history, prev_state):
    # Users get ideas every 10 steps (approximately once every week)
    # Assume that an idea generally takes around 7 MiB. Use a beta distribution
    # with alpha = 2, and beta = 20 to simulate this

    # Choose the closest rate to the going market rate that the user can pay
    # (if their balance is not enough to cover it, just use that)
    return {
        u: (
            None
            if u.last_contract != prev_state["timestep"]
            else Contract(
                None,
                u,
                size,
                -1,
                prev_state["timestep"],
                min(prev_state["mkt_sprice"] * size, u.balance) / size,
                len(prev_state["orders"]),
            )
        )
        for (u, size) in map(
            lambda u: (u[0], u[1] * 100),
            zip(prev_state["users"], beta(2, 20, len(prev_state["users"]))),
        )
    }
