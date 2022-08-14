"""Deals with the creation and management of proposals."""
from dataclasses import dataclass
from random import random, shuffle
from actors.idea import Idea
from actors.user import User
from actors.voting_events import Voting_event
import math


@dataclass
class Proposal:
    """Represents an proposal."""

    # The total amount of votes needed to pass the proposal.
    # Each token gets translated to some amount of votes based onwhich voting mechanism
    # is used.
    required_votes: float

    # The idea which the proposal concerns.
    idea_id: int
    # Unique id for the proposal.
    proposal_id: int

    # Active time of the proposal in ticks plus inital time
    end_time: int

    current_votes: float

    is_passed: bool

    def __init__(self, required_votes, idea_id, proposal_id, end_time):
        """Initialize with the amount of required votes and the proposal id."""
        self.required_votes = required_votes
        self.idea_id = idea_id
        self.proposal_id = proposal_id
        self.end_time = end_time
        self.current_votes = 0
        self.is_passed = None

    def __hash__(self):
        """proposal_id is the hash."""
        return self.proposal_id

    def __eq__(self, o):
        """Equal iff proposal_id's are equal."""
        return self.proposal_id == o.proposal_id


def make_proposal(params, substep, state_history, prev_state, policy_input):
    """User has a chance to make a proposal every 10 ticks on an idea."""
    if prev_state["timestep"] % 10 != 0:
        return ("proposals", prev_state["proposals"])

    new_proposals = []
    for user in prev_state["users"]:
        idea: Idea
        for idea in filter(
            lambda idea: user.user_id in idea.shareholders, prev_state["ideas"]
        ):
            if random() > 0.1:
                continue

            new_proposals.append(
                Proposal(
                    math.floor(random() * 50 + 50),
                    idea.idea_id,
                    len(prev_state["proposals"]) + len(new_proposals),
                    math.floor(random() * 40 + 10) + prev_state["timestep"],
                )
            )

    return ("proposals", [*prev_state["proposals"], *new_proposals])


def vote_on_proposals(params, substep, state_history, prev_state):
    """User has a chance to vote on any proposal that they can vote on."""
    signal = {
        "proposal_votes": {},  # propsal_id -> votes
        "user_frozen_tokens": {},  # user_id -> (proposal_id -> (idea_id, amount))
        "user_lost_tokens": {},  # user_id -> (idea_id -> amount)
        "voting_events": [],  # list of all the voting events that happened here
    }
    user: User
    for user in prev_state["users"]:
        signal["user_frozen_tokens"][user.user_id] = {}
        signal["user_lost_tokens"][user.user_id] = {}

        proposal: Proposal
        for proposal in filter(lambda p: not p.is_passed, prev_state["proposals"]):
            if random() > 0.1 or proposal.idea_id not in user.tokens:
                continue

            available_tokens = user.tokens[proposal.idea_id]

            used_tokens = available_tokens * math.floor(random() * 20 + 20) / 100

            if used_tokens <= 0:
                continue

            (votes, used_tokens, event) = __pass_vote(
                proposal,
                user,
                used_tokens,
                prev_state["users"],
            )

            signal["voting_events"].append(event)

            if votes is None:
                signal["user_lost_tokens"][user.user_id][proposal.idea_id] = (
                    signal["user_lost_tokens"][user.user_id].get(proposal.idea_id, 0)
                    + used_tokens
                )
            else:
                signal["proposal_votes"][proposal.proposal_id] = (
                    signal["proposal_votes"].get(proposal.proposal_id, 0) + votes
                )

                signal["user_frozen_tokens"][user.user_id][proposal.proposal_id] = (
                    proposal.idea_id,
                    signal["user_frozen_tokens"][user.user_id].get(
                        proposal.proposal_id, (0, 0)
                    )[1]
                    + used_tokens,
                )

    return signal


def __pass_vote(proposal: Proposal, voter: User, tokens: float, users: [User]):
    """
    Use quadratic voting. With the enforcer-jury mechanism.

    Returns the votes cast, tokens spent, and the voting event.
    If the votes are None, the user has been found guilty and should lose the tokens
    they voted with.
    """
    event = Voting_event()
    event.real_result_guilty = random() < voter.chance_to_lie

    enforcer_list: [] = list(
        filter(lambda u: u.user_id != voter.user_id and u.balance >= tokens, users)
    )

    shuffle(enforcer_list)

    enforcer = None
    if enforcer_list is not None and len(enforcer_list) > 0:
        enforcer = enforcer_list[0]

    # start jury-enforcer mechanism if there is an enforcer
    # large amount of enforcer's claim is based on the voter's chance to lie since we
    # are assuming the enforcer has special information on the voter
    if enforcer is not None and random() < enforcer.suspicion + voter.chance_to_lie / 3:
        event.enforcer = enforcer

        # random number of jurors (minus 1 for voter in users)
        jury_size = math.ceil(random() * len(users)) - 1

        # No jury, use enforcer's findings
        if jury_size == 0:
            event.jury_verdict_guilty = True

            return (None, tokens, event)

        jury = list(filter(lambda u: u != voter, users))[0 : jury_size - 1]

        shuffle(jury)

        event.jury = jury

        # number of jurors that voted guilty
        # jurors usually will have less information on the voter than the enforcer
        voted_guilty = len(
            list(
                filter(lambda j: random() < j.suspicion + voter.chance_to_lie / 5, jury)
            )
        )

        # 2/3 supermajority required
        if voted_guilty / jury_size >= 2 / 3:
            event.jury_verdict_guilty = True

            return (None, tokens, event)

    return (math.sqrt(tokens), tokens, event)


def process_vote_input(params, substep, state_history, prev_state, policy_input):
    """Process proposal votes on the proposal's side."""
    proposal: Proposal
    for proposal in filter(
        lambda p: p.proposal_id in policy_input["proposal_votes"],
        prev_state["proposals"],
    ):

        proposal.current_votes += policy_input["proposal_votes"][proposal.proposal_id]

    return ("proposals", prev_state["proposals"])


def update_proposal_status(params, substep, state_history, prev_state, policy_input):
    """If the proposal time is up, either pass it or not."""
    proposal: Proposal
    for proposal in prev_state["proposals"]:
        if prev_state["timestep"] != proposal.end_time:
            continue

        proposal.is_passed = proposal.current_votes >= proposal.required_votes

    return ("proposals", prev_state["proposals"])
