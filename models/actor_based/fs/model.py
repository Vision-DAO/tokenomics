from system import update_market_storage_price, update_market_gas_price
from actors.challenge import (
    create_challenges,
    spend_challenge_gas,
    answer_challenges,
    register_challenges,
    update_challenge_counters,
    steal_storage,
    slash_providers,
    reward_enforcers,
    kill_challenges,
    remove_slashed_orders,
)
from actors.buyer import (
    Buyer,
    orphan_bored_users,
    update_last_contract,
    generate_users,
    register_users,
    change_user_head,
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
    release_available_installments,
    add_fulfilled_orders,
    change_order_head,
    generate_orders,
    update_market_price,
    delete_expired_contracts,
    orphan_expired_contracts,
)
from actors.provider import (
    Provider,
    fund_users,
    update_provider_capacities,
    resize_prov_sectors,
    update_expired_provider_capacities,
    generate_providers,
    register_providers,
    change_provider_head,
)

# Start the system off with just one user, who is providing storage to no one
treasury = Provider(100, 51200, 0, 0.0, 1024, 0, 0, 0, 0)
initial_state = {
    # Vision DAO provides 100 GiB of storage, at zero fee
    "treasury": 0,
    "providers": {0: treasury},
    "provider_head": 1,
    "users": {0: Buyer(0, 0, 0, 0, 0, 0, 0, 0)},
    "user_head": 1,
    "orders": [],
    "order_head": 0,
    "active": [],
    # The prevailing storage price: average over the last few time intervals of
    # what users' orders were cleared at. Zero, initially, because the treasury
    # fulfills all orders, unconditionally.
    "mkt_sprice": 0,
    # The price of storage in $ / MiB
    "mkt_fsprice": 0,
    # The price of an Etheruem transaction in $
    "mkt_gprice": 0,
    # The price of 1 VIS (in USD)
    # Assume an initial market cap of $1,000
    "mkt_vprice": 10,
    # Active challenges between an enforcer and a provider
    "challenges": {},
    # Number of MiB of data that was NOT served when it should have been per
    # contract
    "storage_stolen": 0,
}

state_update_blocks = [
    # Update the global storage price based on the expected discount rate in 2
    # years. Also update gas prices
    {
        "policies": {},
        "variables": {
            "mkt_fsprice": update_market_storage_price,
            "mkt_gprice": update_market_gas_price,
        },
    },
    # Resize any provider sectors that are no longer profitable, if they are
    # within their responsiveness periods
    {
        "policies": {},
        "variables": {
            "providers": resize_prov_sectors,
        },
    },
    # Release epoch rewards for all active orders
    {
        "policies": {},
        "variables": {
            "providers": release_available_installments,
        },
    },
    # Replace any orders that have been unfilled for too long, and cancel ones
    # that have gone unfilled for *far* too long
    {
        "policies": {
            "renegotiate_orders": renegotiate_orders,
        },
        "variables": {
            "orders": resubmit_orders,
            "users": orphan_bored_users,
        },
    },
    # Clear out any orders past their expiration date
    {
        "policies": {
            "orphan_expired_contracts": orphan_expired_contracts,
        },
        "variables": {
            "active": delete_expired_contracts,
            "providers": update_expired_provider_capacities,
        },
    },
    # Add 1 new user every 30 ticks
    {
        "policies": {
            "generate_users": generate_users,
        },
        "variables": {
            "users": register_users,
            "user_head": change_user_head,
        },
    },
    # Add 1 new provider every 50 ticks
    {
        "policies": {
            "generate_providers": generate_providers,
        },
        "variables": {
            "providers": register_providers,
            "provider_head": change_provider_head,
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
            "providers": update_treasury_balance,
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
            "order_head": change_order_head,
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
    # Update the next time providers are eligible for challenges within the
    # the context of their contracts, and initiate challenges with providers
    # who are ready
    {
        "policies": {
            "create_challenges": create_challenges,
        },
        "variables": {
            "users": spend_challenge_gas,
            "challenges": register_challenges,
            "active": update_challenge_counters,
        },
    },
    # Produce a proof if we have one, or don't if we took a risk
    {
        "policies": {
            "answer_challenges": answer_challenges,
        },
        "variables": {
            "storage_stolen": steal_storage,
            "providers": slash_providers,
            "users": reward_enforcers,
            "challenges": kill_challenges,
            "active": remove_slashed_orders,
        },
    },
]
