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
import matplotlib.pyplot as plt

idea = Idea(100, 0)
initial_state = {
    "users": [],
    "ideas": [idea],
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


def runner():
    """Run the model."""
    model = Model(
        initial_state=initial_state, state_update_blocks=state_update_blocks, params={}
    )

    simulation = Simulation(model=model, timesteps=200, runs=1)
    result = simulation.run()

    guilty = []
    for step in result:
        if step["substep"] != 1:
            continue

        print(
            sum(map(lambda u: u.balance, step["users"])) / len(step["users"]),
            len(step["users"]),
        )

        print(
            "proposals passed:",
            len(list(filter(lambda p: p.is_passed, step["proposals"]))),
        )

        guilty_ratio: float
        if len(step["voting_events"]) > 0:
            guilty_ratio = len(
                list(filter(lambda v: v.real_result_guilty, step["voting_events"]))
            ) / len(step["voting_events"])
        else:
            guilty_ratio = 0

        guilty.append(
            (
                step["timestep"],
                guilty_ratio * 100,
            )
        )

    plt.plot(*zip(*guilty))
    plt.ylim(0, 100)
    plt.xlabel("timestep")
    plt.ylabel("% guilty verdicts")
    plt.show()


if __name__ == "__main__":
    runner()
