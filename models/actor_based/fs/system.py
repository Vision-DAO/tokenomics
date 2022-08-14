"""Implements counters for global variables, and stochastic processes."""
from math import pow


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
