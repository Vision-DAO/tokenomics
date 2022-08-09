"""Deals with the creation and management of users."""
from dataclasses import dataclass
from random import random


@dataclass
class User:
    """
    Represents a user.

    Can create proposals, vote on proposals, and buy tokens.
    """

    # represents a balance of interchangable currency (not in idea tokens)
    balance: float

    user_id: int

    # dict of token_id -> amount
    tokens: {}

    def __init__(self, balance, user_id):
        """Take the user's initial balance, and the user's ID."""
        self.balance = balance
        self.tokens = {}
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

    return ("users", [*prev_users, User(100, len(prev_users))])


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

            to_buy = round(random(), 3) * (user.balance / len(prev_state["ideas"]))

            if to_buy > idea.treasury:
                to_buy = idea.treasury

            amount_spent += to_buy

            if idea.token_id not in signal["idea_treasury"]:
                signal["idea_treasury"][idea.token_id] = idea.treasury

            if idea.token_id not in signal["idea_new_shareholders"]:
                signal["idea_new_shareholders"][idea.token_id] = set()

            signal["idea_treasury"][idea.token_id] -= to_buy

            signal["idea_new_shareholders"][idea.token_id].add(user.user_id)

            signal["user_new_tokens"][user.user_id][idea.token_id] = (
                signal["user_new_tokens"][user.user_id].get(idea.token_id, 0) + to_buy
            )

        signal["user_amount_spent"][user.user_id] = amount_spent

    return signal


def process_token_buy(params, substep, state_history, prev_state, policy_input):
    """Process the token buy on the users' side."""
    for user in prev_state["users"]:
        user.balance -= policy_input["user_amount_spent"][user.user_id]

        new_tokens = policy_input["user_new_tokens"][user.user_id]
        for token, add_amount in new_tokens.items():
            user.tokens[token] = user.tokens.get(token, 0) + add_amount

    return ("users", prev_state["users"])
