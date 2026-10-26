import math

from game.angel import AngelState
from game.world import Digit, Game, Phase


def place(game, angel, x, y):
    angel.x, angel.y = x, y


def far_angels(game):
    """Park all angels in the far corners so they do not interfere."""
    L = game.layout
    for a, room in zip(game.angels, (1, 3, 7)):
        a.x, a.y = L.origin(room)[0] + 20, L.origin(room)[1] + 20


def test_angel_freezes_in_beam_and_moves_in_the_dark(game):
    p, a = game.player, game.angels[0]
    far_angels(game)
    p.facing = 0.0
    place(game, a, p.x + 120, p.y)
    game.update(0.0, (0, 0), 0.0)
    assert a.state is AngelState.FROZEN
    x0 = a.x
    game.update(0.5, (0, 0), 0.0)
    assert a.x == x0
    game.update(0.0, (0, 0), math.pi)               # turn away: the angel is in the dark now
    game.update(0.5, (0, 0), math.pi)
    assert a.state is AngelState.HUNT and a.x < x0


def test_walls_block_light(game):
    p, a = game.player, game.angels[0]
    far_angels(game)
    place(game, a, game.layout.width / 2 + 160 + 60, p.y + 70)   # in room 6, behind the wall
    p.facing = math.atan2(a.y - p.y, a.x - p.x)
    assert not game.is_lit(a.x, a.y)


def test_blackout_lets_angels_advance_and_ends(game):
    p, a = game.player, game.angels[0]
    far_angels(game)
    place(game, a, p.x + 120, p.y)
    assert game.events.trigger("blackout")[0]
    game.update(0.5, (0, 0), 0.0)
    assert a.state is AngelState.HUNT and a.x < p.x + 120
    game.update(3.0, (0, 0), 0.0)
    assert game.light_possible()


def test_angel_walks_through_doorways_to_the_player(game):
    far_angels(game)
    a = game.angels[0]
    L = game.layout
    place(game, a, *L.center(1))
    game.player.facing = math.pi                     # beam away from the angel
    for _ in range(60 * 40):
        game.update(1 / 60, (0, 0), math.pi)
        if game.phase is Phase.LOST:
            break
    assert game.phase is Phase.LOST                  # it reached the player through the maze


def test_touching_an_angel_loses(game):
    far_angels(game)
    a = game.angels[0]
    place(game, a, game.player.x + 5, game.player.y)
    game.update(0.01, (0, 0), 0.0)
    assert game.phase is Phase.LOST


def test_code_is_sorted_by_room_then_collection_order(game):
    game.collected = [(2, 8, 0), (5, 4, 1), (9, 4, 2)]
    assert game.expected_code() == "592"             # the example from the design document


def test_pickup_and_code_entry_flow(game):
    far_angels(game)
    L, p = game.layout, game.player
    ex, ey = L.exit_point()
    game.interact()
    assert game.collected == [] and not game.code_entry
    p.x, p.y = ex - 30, ey
    game.interact()
    assert not game.code_entry and "code" in game.message          # not all digits yet
    game.digits = [Digit(1, 5, p.x, p.y), Digit(2, 6, p.x + 5, p.y), Digit(3, 6, p.x + 7, p.y)]
    for _ in range(3):
        game.interact()
    assert len(game.collected) == 3 and game.all_digits()
    p.x, p.y = ex - 30, ey
    game.interact()
    assert game.code_entry
    for ch in "000":
        game.type_digit(ch)
    assert game.phase is Phase.PLAYING and game.code_buffer == ""      # wrong code
    for ch in game.expected_code():
        game.type_digit(ch)
    assert game.phase is Phase.FINAL and not game.light_possible()


def test_final_blackout_then_escape(game):
    far_angels(game)
    ex, ey = game.layout.exit_point()
    game.phase = Phase.FINAL
    game.player.x, game.player.y = ex - 20, ey
    game.update(0.01, (0, 0), 0.0)
    assert game.phase is Phase.WON


def test_all_digits_speed_up_angels_and_narrow_the_beam(game):
    base_speed, base_beam = game.angel_speed(), game.beam_angle()
    game.collected = [(1, 1, 0), (2, 2, 1), (3, 3, 2)]
    assert math.isclose(game.angel_speed(), base_speed * 1.3)
    assert game.beam_angle() < base_beam
    game.events.trigger("speed")
    assert math.isclose(game.angel_speed(), base_speed * 1.3 * 1.3)


def test_player_collides_with_walls(game):
    far_angels(game)
    for _ in range(600):
        game.update(1 / 60, (0, -1), 0.0)
    assert game.player.y > 8                          # stopped by the outer wall


def test_shuffle_moves_objects_with_their_rooms(game):
    L = game.layout
    far_angels(game)
    before = [(a.x - L.origin(L.room_of(a.x, a.y))[0], a.y - L.origin(L.room_of(a.x, a.y))[1]) for a in game.angels]
    rooms_before = [L.room_of(a.x, a.y) for a in game.angels]
    player_before = (game.player.x, game.player.y)
    assert game.shuffle_rooms()
    after = [(a.x - L.origin(L.room_of(a.x, a.y))[0], a.y - L.origin(L.room_of(a.x, a.y))[1]) for a in game.angels]
    assert after == before                              # same place inside the (new) room
    assert [L.room_of(a.x, a.y) for a in game.angels] != rooms_before
    assert (game.player.x, game.player.y) == player_before and game.player_room() == L.start_room
    for d in game.digits:
        assert d.room == L.room_of(d.x, d.y)


def test_lock_rules_and_cooldowns(game):
    far_angels(game)
    ok, _ = game.events.trigger("lock", 5)
    assert not ok                                       # never the player's room
    ok, msg = game.events.trigger("lock")
    assert ok and len(game.events.locked) == 1 and game.player_room() not in game.events.locked
    ok, msg = game.events.trigger("lock")
    assert not ok and "cooldown" in msg
    game.update(2.1, (0, 0), 0.0)
    assert not game.events.locked                       # lasts two seconds
    game.update(8.0, (0, 0), 0.0)
    assert game.events.trigger("lock", 2)[0]
    assert not game.events.trigger("lock", 42)[0]
    assert not game.events.trigger("dance")[0]


def test_locked_room_traps_angels_and_blocks_the_route(game):
    L = game.layout
    far_angels(game)
    a = game.angels[0]
    place(game, a, *L.center(4))
    game.player.facing = 0.0
    game.events.locked[4] = 5.0                          # angel sealed inside room 4
    game.update(0.2, (0, 0), 0.0)
    assert a.state is AngelState.BLOCKED
    game.events.locked.clear()
    game.events.locked[6] = 5.0
    b = game.angels[1]
    place(game, b, *L.center(3))
    game.update(0.2, (0, 0), 0.0)
    assert b.state is AngelState.HUNT                    # reroutes around the sealed room


def test_chaos_and_failed_events_cost_no_cooldown(game):
    far_angels(game)
    ok, _ = game.events.trigger("chaos")
    assert ok and game.events.blackout_left > 0 and game.events.shuffle_left > 0
    game.events.blackout_left = 0
    game.phase = Phase.FINAL
    ok, msg = game.events.trigger("blackout")
    assert not ok and game.events.cooldown["blackout"] == 0
    game.phase = Phase.WON
    assert not game.events.trigger("speed")[0]


def test_reset_gives_a_fresh_valid_round(cfgs):
    cfg, layout = cfgs
    g = Game(cfg, layout, seed=1)
    g.phase = Phase.LOST
    g.reset()
    assert g.phase is Phase.PLAYING and len(g.digits) == 3 and len(g.angels) == 3
    assert len({d.room for d in g.digits}) == 3 and g.layout.start_room not in {d.room for d in g.digits}
    assert len({d.value for d in g.digits}) == 3
