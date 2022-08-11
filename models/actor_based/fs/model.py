from radcad import Model, Simulation
import matplotlib.pyplot as plt
from actors.buyer import (
    Buyer,
    orphan_bored_users,
    update_last_contract,
    generate_users,
    register_orders,
    update_funded_balances,
    negotiate_orders,
    update_user_balances,
)
from actors.contract import (
    update_treasury_balance,
    renegotiate_orders,
    resubmit_orders,
    remove_fulfilled_orders,
    add_fulfilled_orders,
    generate_orders,
    update_market_price,
    orphan_expired_contracts,
)
from actors.provider import Provider, fund_users, update_provider_capacities
import pandas as pd

# Start the system off with just one user, who is providing storage to no one
treasury = Provider(100, 51200, 0, 0, 0)
initial_state = {
    # Vision DAO provides 100 GiB of storage, at zero fee
    "treasury": treasury,
    "providers": [treasury],
    "users": [Buyer(0, 0, 0, 0, 0, 0, 0)],
    "orders": [],
    "active": [],
    # The prevailing storage price: average over the last few time intervals of
    # what users' orders were cleared at. Zero, initially, because the treasury
    # fulfills all orders, unconditionally.
    "mkt_sprice": 0,
}

state_update_blocks = [
    # Clear out any contracts that are past their expiration date, replace
    # any orders that have been unfilled for too long, and cancel ones that
    # have gone unfilled for *far* too long
    {
        "policies": {
            "renegotiate_orders": renegotiate_orders,
        },
        "variables": {
            "active": orphan_expired_contracts,
            "orders": resubmit_orders,
            "users": orphan_bored_users,
        },
    },
    # Add 1 new user every 30 ticks
    {
        "policies": {},
        "variables": {
            "users": generate_users,
        },
    },
    # Make sure any user without any funds recives a grant of 0.5% of the Vision
    # treasury
    {
        "policies": {
            "fund_users": fund_users,
        },
        "variables": {
            "users": update_funded_balances,
            "treasury": update_treasury_balance,
        },
    },
    # Mark any users that have not had a new idea in the last 10 ticks.
    # They are up for a new DAO
    {
        "policies": {},
        "variables": {
            "users": update_last_contract,
        },
    },
    # Create file storage orders for users with new ideas
    {
        "policies": {
            "generate_orders": generate_orders,
        },
        "variables": {
            "orders": register_orders,
            "users": update_user_balances,
        },
    },
    # Allow users to adjust their orders based on how much they like Vision,
    # and how big their balances are
    {
        "policies": {
            "negotiate_orders": negotiate_orders,
        },
        "variables": {
            "orders": remove_fulfilled_orders,
            "providers": update_provider_capacities,
            "active": add_fulfilled_orders,
            "mkt_sprice": update_market_price,
        },
    },
]
