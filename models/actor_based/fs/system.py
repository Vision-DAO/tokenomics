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


def calc_market_vis_price(params, substep, state_history, prev_state):
    mkt_price = prev_state["mkt_vprice"]
    v_demand = prev_state["v_demand"]
    v_supply = prev_state["v_supply"]

    providers = prev_state["providers"]
    users = prev_state["users"]

    for (price, (q_s, sellers)) in v_supply.items():
        # print(price)
        if price not in prev_state["v_demand"]:
            continue

        (q_d, buyers) = prev_state["v_demand"][price]

        if q_d == q_s:
            mkt_price = price

        for buyer, size in buyers.items():
            providers[buyer].balance += size
            v_demand[price][0] -= size
            v_supply[price][0] -= size

        for seller, size, kind in sellers:
            if kind == 0 and seller in providers:
                providers[seller].balance -= size
            elif kind == 1 and seller in users:
                users[seller].balance -= size

    return {
        "mkt_vprice": mkt_price,
        "v_demand": v_demand,
        "v_supply": v_supply,
        "providers": providers,
        "users": users,
    }


def update_market_vis_price(params, substep, state_history, prev_state, policy_input):
    return ("mkt_vprice", policy_input["mkt_vprice"])


def fill_market_vis_demand(params, substep, state_history, prev_state, policy_input):
    return ("v_demand", policy_input["v_demand"])


def fill_market_vis_supply(params, substep, state_history, prev_states, policy_input):
    return ("v_supply", policy_input["v_supply"])


def deliver_user_vis_supply(params, substep, state_history, prev_state, policy_input):
    return ("users", policy_input["users"])


def deliver_market_vis_demand(params, substep, state_history, prev_state, policy_input):
    return ("providers", policy_input["providers"])


def sell_bored_user_funds(params, substep, state_history, prev_state, policy_input):
    supply = prev_state["v_supply"]

    for u in prev_state["users"].values():
        if u.all_orders == 0 or u.unfilled_orders / u.all_orders <= u.ux_tolerance:
            price = round(u.stinginess * prev_state["mkt_vprice"], 2)
            if price not in supply:
                supply[price] = [0, []]

            supply[price][0] += u.balance

    # Sell the funds at a lower price since we're leaving
    return ("v_supply", supply)


def take_profit_for(kind, u, prev_state):
    if prev_state["timestep"] % u.sell_interval != 0:
        return 0

    return u.balance * u.sell_pct


def take_profit(params, substep, state_history, prev_state, policy_input):
    supply = prev_state["v_supply"]

    for u in prev_state["users"].values():
        price = round(prev_state["mkt_vprice"] * u.stinginess, 2)

        if price not in supply:
            supply[price] = [0, []]

        q = take_profit_for(1, u, prev_state)
        supply[price][0] += take_profit_for(1, u, prev_state)
        supply[price][1].append([u.id, q, 1])

    for prov in prev_state["providers"].values():
        price = round(prev_state["mkt_vprice"] * (prov.risk_tolerance + 1), 2)

        if price not in supply:
            supply[price] = [0, []]

        q = take_profit_for(0, prov, prev_state)
        supply[price][0] += take_profit_for(0, prov, prev_state)
        supply[price][1].append([prov.id, q, 0])

    return ("v_supply", supply)
