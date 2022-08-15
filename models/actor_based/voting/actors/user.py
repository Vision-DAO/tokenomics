"""Deals with the creation and management of users."""
from dataclasses import dataclass
from random import random, uniform
from numpy.random import normal


@dataclass
class User:
    """
    Represents a user.

    Can create proposals, vote on proposals, and buy tokens.
    """

    # represents a balance of interchangable currency (not in idea tokens)
    balance: float

    user_id: int

    # 0 to 1 chance of whether a user will commit voter fraud
    chance_to_lie: float
    # proclivity to vote guilty if on a jury or elected as enforcer.
    # 0-100% chance to vote guilty/not guilty
    suspicion: float

    # dict of idea_id -> amount
    tokens: {}

    # dict of proposal_id -> amount
    frozen: {}

    def __init__(self, balance, user_id, chance_to_lie, suspicion):
        """Take the user's initial balance, and the user's ID."""
        self.balance = balance
        self.chance_to_lie = chance_to_lie
        self.suspicion = suspicion
        self.tokens = {}
        self.frozen = {}
        self.user_id = user_id

    def __hash__(self):
        """user_id is the hash."""
        return self.user_id

    def __eq__(self, o):
        """Equal iff user_id's are equal."""
        return self.user_id == o.user_id


def generate_users(params, substep, state_history, prev_state, policy_input):
    """Add a new user every some params["ticks_per_user"] ticks."""
    prev_users = prev_state["users"]

    if prev_state["timestep"] % params["ticks_per_user"] != 0:
        return ("users", prev_users)

    user = User(
        params["user_starting_VIS"],
        len(prev_users),
        min(1, max(0, normal(params["user_lie_mean"], 0.5))),
        min(1, max(0, normal(params["user_sus_mean"], 0.5))),
    )

    return (
        "users",
        [*prev_users, user],
    )


def buy_token(params, substep, state_history, prev_state):
    """See if any user would like to buy any tokens, then buy them."""
    signal: dict = {
        "user_amount_spent": {},
        "user_new_tokens": {},
        "idea_treasury": {},
        "idea_new_shareholders": {},
    }

    for user in prev_state["users"]:
        # some chance to buy each token, taking a scaled random amount of their balance.
        amount_spent = 0

        signal["user_new_tokens"][user.user_id] = {}
        signal["user_amount_spent"][user.user_id] = 0

        for idea in prev_state["ideas"]:

            if random() > params["user_chance_to_buy_token"]:
                continue

            to_buy = uniform(
                params["user_token_buy_precent_range"][0],
                params["user_token_buy_precent_range"][1],
            ) * (user.balance - amount_spent)

            if to_buy > idea.treasury:
                to_buy = idea.treasury

            amount_spent += to_buy

            if idea.idea_id not in signal["idea_treasury"]:
                signal["idea_treasury"][idea.idea_id] = idea.treasury

            if idea.idea_id not in signal["idea_new_shareholders"]:
                signal["idea_new_shareholders"][idea.idea_id] = set()

            signal["idea_treasury"][idea.idea_id] -= to_buy

            signal["idea_new_shareholders"][idea.idea_id].add(user.user_id)

            signal["user_new_tokens"][user.user_id][idea.idea_id] = (
                signal["user_new_tokens"][user.user_id].get(idea.idea_id, 0) + to_buy
            )

        signal["user_amount_spent"][user.user_id] = amount_spent

    return signal


def pay_users(params, substep, state_history, prev_state, policy_input):
    """Pay users some VIS every few ticks specified by params."""
    if (
        prev_state["timestep"] % params["ticks_per_VIS_gift"] != 0
        or not params["ticks_per_VIS_gift"]
    ):
        return ("users", prev_state["users"])

    user: User
    for user in prev_state["users"]:
        user.balance += params["VIS_gift_amount"]

    return ("users", prev_state["users"])


def process_token_buy(params, substep, state_history, prev_state, policy_input):
    """Process the token buy on the users' side."""
    for user in filter(
        lambda u: u.user_id in policy_input["user_amount_spent"], prev_state["users"]
    ):
        user.balance -= policy_input["user_amount_spent"][user.user_id]

        new_tokens = policy_input["user_new_tokens"][user.user_id]
        for token, add_amount in new_tokens.items():
            user.tokens[token] = user.tokens.get(token, 0) + add_amount

    return ("users", prev_state["users"])


def process_vote_output(params, substep, state_history, prev_state, policy_input):
    """Process the tokens used for proposal votes on the user's side."""
    for user in filter(
        lambda u: u.user_id in policy_input["user_frozen_tokens"], prev_state["users"]
    ):
        lost = policy_input["user_frozen_tokens"][user.user_id]
        for proposal_id, (idea_id, remove_amount) in lost.items():
            user.frozen[proposal_id] = (
                idea_id,
                user.frozen.get(proposal_id, (0, 0))[0] + remove_amount,
            )

            user.tokens[idea_id] -= remove_amount

            # might be negative due to floating point rounding
            if user.tokens[idea_id] < 0:
                user.tokens[idea_id] = 0

    for user in filter(
        lambda u: u.user_id in policy_input["user_lost_tokens"], prev_state["users"]
    ):
        lost = policy_input["user_lost_tokens"][user.user_id]
        for token, remove_amount in lost.items():
            user.tokens[token] -= remove_amount

            # might be negative due to floating point rounding
            if user.tokens[token] < 0:
                user.tokens[token] = 0

    return ("users", prev_state["users"])


def unfreeze_tokens(params, substep, state_history, prev_state, policy_input):
    """Unfreeze tokens if a proposal is finished."""
    user: User
    for user in prev_state["users"]:
        for proposal_id in user.frozen:

            proposal = list(
                filter(lambda p: p.proposal_id == proposal_id, prev_state["proposals"])
            )[0]

            if not proposal.is_passed:
                continue

            idea_id, amount = user.frozen[proposal_id]
            user.tokens[idea_id] += amount

    return ("users", prev_state["users"])
