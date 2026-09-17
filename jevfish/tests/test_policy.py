import random

from jevfish.judge import ChoiceA, NoulA, ScoreA, Verdict
from jevfish.platforms.base import ACTIONS, FeedComment, FeedPost
from jevfish.policy import Mind, allowed_actions, build_questions, decide, feed_view, poll_questions, stance_label
from jevfish.fakes import frame as fake_frame
from jevfish.frame import normalize_frame

FRAME = normalize_frame(fake_frame([{"role": "user", "content": "Prediction question: Will it work?"}]))
AGENT = {"agent_id": 5, "name": "Ana", "bio": "nurse", "persona": "p", "segment": "renters", "attributes": {"budget": "low"},
         "stance_hint": "against", "kind": "public", "follows": [1]}


def certain(option, options):
    return ChoiceA(option, {o: (1.0 if o == option else 0.0) for o in options}, 1.0)


def test_actions_depend_on_the_feed():
    mind = Mind(AGENT, following={1})
    assert allowed_actions(ACTIONS["reddit"], [], mind, 5, set()) == ["do_nothing", "create_post"]
    feed = [FeedPost(1, 1, "hi"), FeedPost(2, 2, "yo", comments=[FeedComment(9, 3, "c")])]
    got = allowed_actions(ACTIONS["reddit"], feed, mind, 5, set())
    assert set(got) == set(ACTIONS["reddit"])
    mind.liked_posts |= {1, 2}
    mind.liked_comments |= {9}
    got = allowed_actions(ACTIONS["reddit"], feed, mind, 5, {2})
    assert "like_post" not in got and "like_comment" not in got and "follow" not in got
    assert "dislike_post" in got and "create_comment" in got


def test_questions_and_views():
    mind = Mind(AGENT, stance=3.4, following={1})
    feed = [FeedPost(1, 1, "hi", comments=[FeedComment(9, 3, "c")]), FeedPost(2, 2, "yo")]
    labels = {1: "Bob (x)", 2: "Cy (y)", 3: "Di (z)"}
    actions = allowed_actions(ACTIONS["reddit"], feed, mind, 5, set())
    qs = build_questions(FRAME, feed, actions, labels, mind, 5, set())
    assert set(qs) == {"stance", "outcome", "action", "point", "target_post", "target_comment", "followee"}
    assert "none" in qs["point"].criteria
    assert set(qs["target_post"].criteria) == {"p1", "p2"}
    assert set(qs["followee"].criteria) == {"u2"}
    view = feed_view(feed, labels, mind.following)
    assert view[0]["author_is_followed"] and view[0]["comments"][0]["comment_id"] == "c9"
    assert stance_label(FRAME["stance"]["levels"], 3.4) == FRAME["stance"]["levels"][3]
    assert stance_label(FRAME["stance"]["levels"], None) == "has not formed a view yet"
    assert set(poll_questions(FRAME)) == {"stance", "outcome"}
    only_nothing = build_questions(FRAME, [], ["do_nothing"], labels, mind, 5, set())
    assert set(only_nothing) == {"stance", "outcome"}


def test_decide_respects_exclusions():
    answers = {
        "stance": ScoreA(2.0, {2: 1.0}, 1.0),
        "outcome": NoulA(0.4),
        "action": certain("like_post", ["like_post", "do_nothing"]),
        "target_post": ChoiceA("p1", {"p1": 0.9, "p2": 0.1}, 0.5),
    }
    d = decide(Verdict(answers, 1, 1), random.Random(0), 5, {"like_post": {1}})
    assert d.action == "like_post" and d.target_post == 2
    d = decide(Verdict(answers, 1, 1), random.Random(0), 5, {"like_post": {1, 2}})
    assert d.target_post is None
    no_action = decide(Verdict({k: answers[k] for k in ("stance", "outcome")}, 1, 1), random.Random(0), 5)
    assert no_action.action == "do_nothing" and no_action.outcome_p == 0.4
