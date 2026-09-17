import pytest

from jevfish.platforms import Act, make_platform

AGENTS = [
    {"agent_id": 0, "username": "ana", "bio": "nurse", "persona": "p", "follows": [1]},
    {"agent_id": 1, "username": "raj", "bio": "engineer", "persona": "p", "follows": [0, 2]},
    {"agent_id": 2, "username": "mei", "bio": "student", "persona": "p", "follows": [0]},
]


@pytest.fixture(params=["lite", "reddit"])
async def platform(request, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # OASIS creates ./log on import
    p = make_platform(request.param, tmp_path / request.param)
    await p.start(AGENTS)
    yield p
    await p.close()


async def test_post_like_comment_flow(platform):
    await platform.refresh_recommendations()
    assert await platform.feed(1) == []
    r = await platform.apply([Act(0, "create_post", {"content": "Weekly cleaning is worth it"})])
    assert r[0]["ok"], r
    assert await platform.feed(1) == [] or platform.name != "lite"  # lite hides posts until the next refresh
    await platform.refresh_recommendations()
    feed = await platform.feed(1)
    assert [p.content for p in feed] == ["Weekly cleaning is worth it"]
    assert await platform.feed(0) == []  # never your own post
    pid = feed[0].post_id
    r = await platform.apply([
        Act(1, "like_post", {"post_id": pid}),
        Act(2, "create_comment", {"post_id": pid, "content": "Depends on the housemates"}),
    ])
    assert all(x["ok"] for x in r), r
    await platform.refresh_recommendations()
    post = (await platform.feed(2))[0]
    assert post.likes == 1
    assert [c.content for c in post.comments] == ["Depends on the housemates"]
    cid = post.comments[0].comment_id
    r = await platform.apply([Act(0, "like_comment", {"comment_id": cid}), Act(1, "do_nothing", {})])
    assert all(x["ok"] for x in r), r
    all_posts = await platform.posts()
    assert len(all_posts) == 1 and all_posts[0]["likes"] == 1
    assert all_posts[0]["comments"][0]["likes"] == 1
    assert all_posts[0]["comments"][0]["author_id"] == 2


async def test_bad_target_is_reported_not_raised(platform):
    r = await platform.apply([Act(0, "like_post", {"post_id": 999})])
    assert r[0]["ok"] is False


async def test_twitter_style_repost_on_lite(tmp_path):
    p = make_platform("lite", tmp_path)
    await p.start(AGENTS)
    await p.apply([Act(0, "create_post", {"content": "original"})])
    await p.refresh_recommendations()
    pid = (await p.feed(1))[0].post_id
    await p.apply([Act(1, "repost", {"post_id": pid})])
    await p.refresh_recommendations()
    posts = await p.posts()
    assert posts[0]["shares"] == 1 and posts[1]["kind"] == "repost" and posts[1]["original_post_id"] == pid
    feed = await p.feed(2)
    assert len(feed) == 1  # original and its repost collapse into one item


def test_unknown_platform():
    with pytest.raises(ValueError):
        make_platform("myspace", ".")


async def test_duplicate_likes_are_rejected(platform):
    await platform.apply([Act(0, "create_post", {"content": "hello"})])
    await platform.refresh_recommendations()
    pid = (await platform.feed(1))[0].post_id
    first = await platform.apply([Act(1, "like_post", {"post_id": pid})])
    second = await platform.apply([Act(1, "like_post", {"post_id": pid})])
    assert first[0]["ok"] and not second[0]["ok"]
