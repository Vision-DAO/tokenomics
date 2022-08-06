from radcad import Model
from . actors import provider.Provider, provider.generate_providers, buyer.generate_orders, buyer.update_last_contract, buyer.generate_users, provider.fund_users

# Start the system off with just one user, who is providing storage to no one
treasury = Provider(100, 102400, 0, 0, {})
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
        "policies": {},
        "variables": {
            "orders": generate_orders,
        },
    },
    # Allow users to adjust their orders based on how much they like Visoin, and
    # how big their balances are
    {
        "policies": {
            "negotiate_orders": negotiate_orders,
        },
        "variables": {
        },
    },
]

def runner():
    model = Model(initial_state=initial_state, state_update_blocks=state_update_blocks, params={})

if __name__ == "__main__":
    runner()
