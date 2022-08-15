"""Implements counters for global variables, and stochastic processes."""
from math import pow
from numpy.random import normal


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
