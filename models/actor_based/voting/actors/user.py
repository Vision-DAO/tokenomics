"""Deals with the creation and management of users."""
from dataclasses import dataclass
from random import random
import math


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
    """Add a new user every 30 ticks."""
    prev_users = prev_state["users"]

    if prev_state["timestep"] % 30 != 0:
        return ("users", prev_users)

    return ("users", [*prev_users, User(100, len(prev_users), random(), random())])


def buy_token(params, substep, state_history, prev_state):
    """See if any user would like to buy any tokens, then buy them."""
    signal: dict = {
        "user_amount_spent": {},
        "user_new_tokens": {},
        "idea_treasury": {},
        "idea_new_shareholders": {},
    }

    for user in prev_state["users"]:
        # 10% chance to buy each token, taking a scaled random amount of their balance.
        amount_spent = 0

        signal["user_new_tokens"][user.user_id] = {}
        signal["user_amount_spent"][user.user_id] = 0

        for idea in prev_state["ideas"]:

            if random() >= 0.1:
                continue

            to_buy = (
                math.floor(random() * 100)
                / 100
                * (user.balance / len(prev_state["ideas"]))
            )

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
    """Pay users 50 VIS every 50 ticks."""
    if prev_state["timestep"] % 50 != 0:
        return ("users", prev_state["users"])

    user: User
    for user in prev_state["users"]:
        user.balance += 50

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
        for token, remove_amount in lost.items():
            user.frozen[token] = user.frozen.get(token, 0) + remove_amount

            user.tokens[token] -= remove_amount

            # might be negative due to floating point rounding
            if user.tokens[token] < 0:
                user.tokens[token] = 0

    for user in filter(
        lambda u: u.user_id in policy_input["user_lost_tokens"], prev_state["users"]
    ):
        lost = policy_input["user_frozen_tokens"][user.user_id]
        for token, remove_amount in lost.items():
            user.tokens[token] -= remove_amount

            # might be negative due to floating point rounding
            if user.tokens[token] < 0:
                user.tokens[token] = 0

    return ("users", prev_state["users"])
