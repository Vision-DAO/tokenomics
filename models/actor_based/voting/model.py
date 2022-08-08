"""Models the voting mechanisms of Vision."""
from radcad import Model, Simulation
from actors.idea import Idea
from actors.user import generate_users
import pandas as pd

idea = Idea(100, 0)
initial_state = {
    "users": [],
    "ideas": [idea],
    "proposals": [],
}


state_update_blocks = [
    # Add 1 new user every 30 ticks
    {
        "policies": {},
        "variables": {
            "users": generate_users,
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

    df = pd.DataFrame(result)
    print(df)


if __name__ == "__main__":
    runner()
