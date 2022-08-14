"""Models the voting mechanisms of Vision."""
from radcad import Model, Simulation
from actors.idea import (
    Idea,
    generate_ideas,
    process_token_sell,
)
from actors.user import (
    generate_users,
    buy_token,
    process_token_buy,
    process_vote_output,
    pay_users,
)
from actors.proposal import (
    make_proposal,
    vote_on_proposals,
    process_vote_input,
    update_proposal_status,
)
from actors.voting_events import process_voting_events

initial_state = {
    "users": [],
    "ideas": [Idea(100, 0)],
    "proposals": [],
    "voting_events": [],
}


state_update_blocks = [
    # add 1 new user every 30 ticks
    {
        "policies": {},
        "variables": {
            "users": generate_users,
        },
    },
    # pay users every 50 ticks
    {
        "policies": {},
        "variables": {
            "users": pay_users,
        },
    },
    # add 1 new idea every 45 ticks
    {
        "policies": {},
        "variables": {
            "ideas": generate_ideas,
        },
    },
    {
        "policies": {
            "buy_token": buy_token,
        },
        "variables": {
            "users": process_token_buy,
            "ideas": process_token_sell,
        },
    },
    {
        "policies": {},
        "variables": {
            "proposals": make_proposal,
        },
    },
    {
        "policies": {
            "vote_on_proposals": vote_on_proposals,
        },
        "variables": {
            "voting_events": process_voting_events,
            "users": process_vote_output,
            "proposals": process_vote_input,
        },
    },
    {
        "policies": {},
        "variables": {
            "proposals": update_proposal_status,
        },
    },
]
