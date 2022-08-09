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
)
import pandas as pd

idea = Idea(100, 0)
initial_state = {
    "users": [],
    "ideas": [idea],
    "proposals": [],
}


state_update_blocks = [
    # add 1 new user every 30 ticks
    {
        "policies": {},
        "variables": {
            "users": generate_users,
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
]


def runner():
    """Run the model."""
    model = Model(
        initial_state=initial_state, state_update_blocks=state_update_blocks, params={}
    )

    simulation = Simulation(model=model, timesteps=60, runs=1)
    result = simulation.run()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.expand_frame_repr", False)
    pd.set_option("max_colwidth", None)

    df = pd.DataFrame(result)
    df.set_index(["run", "timestep", "substep"])
    print(df.loc[:, "users"][3::3])

    print(df.loc[:, "ideas"][3::3])


if __name__ == "__main__":
    runner()
