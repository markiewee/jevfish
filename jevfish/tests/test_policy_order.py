from jevfish.policy import NO_POINT, shuffled_criteria


def test_same_seed_and_person_give_the_same_order():
    c = {"a": "A", "b": "B", "c": "C", "d": "D"}
    assert list(shuffled_criteria(c, seed=1, agent_id=7)) == list(
        shuffled_criteria(c, seed=1, agent_id=7)
    )


def test_different_people_get_different_orders():
    c = {f"k{i}": f"V{i}" for i in range(8)}
    orders = {tuple(shuffled_criteria(c, seed=1, agent_id=i)) for i in range(20)}
    assert len(orders) > 1


def test_different_seeds_give_different_orders_for_the_same_person():
    c = {f"k{i}": f"V{i}" for i in range(8)}
    orders = {tuple(shuffled_criteria(c, seed=s, agent_id=3)) for s in range(20)}
    assert len(orders) > 1


def test_contents_are_preserved_exactly():
    c = {"a": "A", "b": "B", "c": "C"}
    assert dict(shuffled_criteria(c, seed=3, agent_id=2)) == c


def test_reserved_none_option_stays_last():
    c = {"x": "X", NO_POINT: "None of these", "y": "Y", "z": "Z"}
    for agent_id in range(30):
        out = list(shuffled_criteria(c, seed=1, agent_id=agent_id, pin_last=frozenset({NO_POINT})))
        assert out[-1] == NO_POINT


def test_every_position_gets_used_across_the_crowd():
    """The point of the exercise: no option is stuck in one slot."""
    c = {"a": "A", "b": "B", "c": "C"}
    positions = {k: set() for k in c}
    for agent_id in range(60):
        for i, k in enumerate(shuffled_criteria(c, seed=0, agent_id=agent_id)):
            positions[k].add(i)
    assert all(len(v) == 3 for v in positions.values())


def test_a_single_option_is_left_alone():
    assert list(shuffled_criteria({"only": "O"}, seed=1, agent_id=1)) == ["only"]
    assert shuffled_criteria({}, seed=1, agent_id=1) == {}
