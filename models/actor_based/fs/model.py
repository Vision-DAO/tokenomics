from radcad import Model, Simulation
from actors.buyer import update_last_contract, \
    generate_users, register_orders, update_funded_balances, \
    negotiate_orders, update_user_balances
from actors.contract import update_treasury_balance, \
    remove_fulfilled_orders, add_fulfilled_orders, \
    generate_orders
from actors.provider import Provider, fund_users, update_provider_capacities
import pandas as pd

# Start the system off with just one user, who is providing storage to no one
treasury = Provider(100, 102400, 0, 0)
initial_state = {
    # Vision DAO provides 100 GiB of storage, at zero fee
    "treasury": treasury,
    "providers": [treasury],
    "users": [],
    "orders": [],
    "active": [],

    # The prevailing storage price: average over the last few time intervals of
    # what users' orders were cleared at. Zero, initially, because the treasury
    # fulfills all orders, unconditionally.
    "mkt_sprice": 0,
}

state_update_blocks = [
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
    # Allow users to adjust their orders based on how much they like Visoin, and
    # how big their balances are
    {
        "policies": {
            "negotiate_orders": negotiate_orders,
        },
        "variables": {
            "orders": remove_fulfilled_orders,
            "providers": update_provider_capacities,
            "active": add_fulfilled_orders,
        },
    },
]

def runner():
    model = Model(initial_state=initial_state, state_update_blocks=state_update_blocks, params={})
    simulation = Simulation(model=model, timesteps=10, runs=1)
    result = simulation.run()

    df = pd.DataFrame(result)
    print(df)

if __name__ == "__main__":
    runner()
