"""Implements methods for creating, and interacting with contracts."""

from .provider import Provider
from .buyer import Buyer
from numpy.random import beta, normal
from dataclasses import dataclass
from functools import reduce
from math import floor, ceil
from itertools import count


@dataclass
class Contract:
    """Represent an agreement between a storage provider and user."""

    provider: Provider
    buyer: Buyer
    size: float
    next_epoch: int
    n_epochs: int
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
            *prev_state["active"],
            *[
                Contract(
                    prov,
                    order.buyer,
                    order.size,
                    order.n_epochs,
                    prev_state["timestep"] + 1,
                    order.epoch_created_at,
                    order.price,
                    order.id,
                )
                for (order, prov) in policy_input["filled"].items()
            ],
        ],
    )


def generate_orders(params, substep, state_history, prev_state):
    # Users get ideas every 10 steps (approximately once every week)
    mu, sig = (
        params["avg_contract_epochs"] if "avg_contract_epochs" in params else (100, 20)
    )

    # Assume that an idea generally takes around 20 MiB in total. Use a beta
    # distribution
    # with alpha = 5, and beta = 20 to simulate this
    sizes = map(lambda x: ceil(x * 100), beta(5, 20, len(prev_state["users"])))

    # The new starting ID of contracts to create
    base_id = (
        max(
            prev_state["orders"][-1].id if len(prev_state["orders"]) > 0 else -1,
            prev_state["active"][-1].id if len(prev_state["active"]) > 0 else -1,
        )
        + 1
    )

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
                floor(normal(mu, sig)),
                -1,
                prev_state["timestep"],
                min(
                    prev_state["mkt_sprice"]
                    * size
                    * (u.stinginess if u.stinginess < 0 else 1),
                    u.balance,
                )
                / size,
                id,
            )
        )
        for (u, size, id) in map(
            lambda u: (u[0], u[1] * 100, u[2]),
            zip(prev_state["users"], sizes, count(start=base_id)),
        )
    }


def update_market_price(params, substep, state_history, prev_state, policy_input):
    if len(policy_input["filled"]) == 0:
        return ("mkt_sprice", 0)

    return (
        "mkt_sprice",
        reduce(lambda s, order: s + order.price, policy_input["filled"].keys(), 0)
        / len(policy_input["filled"]),
    )


def orphan_expired_contracts(params, substep, state_history, prev_state, policy_input):
    return ("active", [o for o in prev_state["active"] if o.n_epochs > 0])


def renegotiate_orders(params, substep, state_history, prev_state):
    timeout_dur = (
        params["order_timeout_interval"] if "order_timeout_interval" in params else 15
    )
    resubmit_dur = (
        params["order_resubmit_interval"] if "order_resubmit_interval" in params else 5
    )

    # Find orders that are eligible for resubmission, and ones that can stay the way they are
    orders = []
    users_affected = {}

    # User balances changed within this substep
    d_balances = {}

    for o in prev_state["orders"]:
        if o.buyer not in d_balances:
            d_balances[o.buyer] = 0

        # Skip orders that are past the point of return
        if prev_state["timestep"] - o.epoch_created_at >= timeout_dur:
            d_balances[o.buyer] -= o.price * o.size

            if o.buyer not in users_affected:
                users_affected[o.buyer] = 0

            users_affected[o.buyer] += 1

            continue

        if prev_state["timestep"] - o.epoch_created_at < resubmit_dur:
            orders.append(o)

            continue

        d_price = o.price - prev_state["mkt_sprice"] * o.buyer.stinginess

        # Re-negotiate the order by upping or lowering the price according to
        # the user's stinginess factor (if they are willing to up their price)
        if (
            o.buyer.stinginess <= 0
            or o.buyer.balance - d_balances[o.buyer] - d_price * o.size
        ):
            orders.append(o)

            continue

        d_balances[o.buyer] += d_price * o.size

        # Up the user's price by whatever they're willing to go up by
        orders.append(
            Contract(
                o.provider,
                o.buyer,
                o.size,
                o.next_epoch,
                o.n_epochs,
                prev_state["timestep"],
                o.price + d_price,
                o.id,
            )
        )

    return {
        "orders": orders,
        "user_counts": users_affected,
        "user_balances": d_balances,
    }


def resubmit_orders(params, substep, state_history, prev_state, policy_input):
    return ("orders", policy_input["orders"])
