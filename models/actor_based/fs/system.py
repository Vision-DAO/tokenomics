"""Implements counters for global variables, and stochastic processes."""
from math import pow
from numpy.random import beta, normal
from random import randrange
from actors.provider import Provider
from actors.buyer import Buyer


def update_market_storage_price(
    params, substep, state_history, prev_state, policy_input
):
    """
    Set the global base price of file storage to the newly calculated rate.

    Based on the number of days into discounts we are (storage $ decreases over
    time with tech advancements)
    """
    base_price = params.get("base_storage_price", 0.00020866669)

    if prev_state["mkt_fsprice"] == 0:
        return ("mkt_fsprice", base_price)

    discount_rate = params.get("d_biyear_storage_price", 0.5)

    return (
        "mkt_fsprice",
        base_price
        * pow(
            discount_rate, prev_state["timestep"] / params.get("ticks_per_year", 128)
        ),
    )


def update_market_gas_price(params, substep, state_history, prev_state, policy_input):
    """
    Update the global price of executing an Etherum transaction through params.

    Assume prices fall along a normal distribution using the mu and sigma
    defined in the analysis.org file.
    """
    (mu, sigma) = params.get("gas_price_dist", (0.1, 0.025))

    return ("mkt_gprice", normal(mu, sigma))


def calc_market_vis_price(params, substep, state_history, prev_state):
    return {
        "mkt_vprice": prev_state["mkt_vprice"]
        + prev_state["mkt_vprice"] * normal(*params.get("d_vis_per_block", (0, 0.025))),
    }


def update_market_vis_price(params, substep, state_history, prev_state, policy_input):
    return ("mkt_vprice", policy_input["mkt_vprice"])


def deliver_user_vis_supply(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])


def deliver_market_vis_demand(params, substep, state_history, prev_state, policy_input):
    return ("providers", policy_input["providers"])


def take_profit_for(kind, u, prev_state):
    if prev_state["timestep"] % u.sell_interval != 0:
        return 0

    return u.balance * u.sell_pct


def perform_random_transfers(params, substep, state_history, prev_state):
    """Schedule a transfer of some random amount of VIS between two random users."""

    if prev_state["timestep"] % params.get("random_transfer_rate", 5):
        return {"providers": prev_state["providers"], "users": prev_state["users"]}

    # Pick two users to subtract a balance form and add to
    all_users = [*prev_state["providers"].values(), *prev_state["users"].values()]
    (sender, recipient) = [randrange(0, len(all_users)) for x in range(2)]

    # Generate an amount to send
    amt = (
        beta(*params.get("profit_taking_amt_dist", [1, 5])) * all_users[sender].balance
    )

    all_users[sender].balance -= amt
    all_users[recipient].balance += amt

    return {
        "providers": {u.id: u for u in all_users if isinstance(u, Provider)},
        "users": {u.id: u for u in all_users if isinstance(u, Buyer)},
    }


def register_transfers_prov(params, substep, state_history, prev_state, policy_input):
    return ("providers", policy_input["providers"])


def register_transfers_user(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])
