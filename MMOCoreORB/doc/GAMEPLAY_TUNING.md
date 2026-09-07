# Master skills, movement, stimpacks and direct travel

These changes build on the 100x credit reduction described in `CREDIT_ECONOMY.md`.

## Master-box bonuses

| Skill box | Additional modifier |
| --- | --- |
| Master Dancer (`social_dancer_master`) | +25 Dancing Mind Enhancement (`healing_dance_mind`) |
| Master Musician (`social_musician_master`) | +25 Musical Mind Enhancement (`healing_music_mind`) |
| Master Doctor (`science_doctor_master`) | +25 Wound Treatment (`healing_wound_treatment`) |
| Master Doctor (`science_doctor_master`) | +25 Wound Treatment Speed (`healing_wound_speed`) |

The bonuses are added to the loaded skill definitions; they do not replace the
existing values. Training and surrender use those definitions. Login reconciles
saved skill modifiers with the definitions, so existing masters receive the
increase without retraining and repeated logins do not stack it. Other skill
boxes, costs, requirements and abilities retain their existing definitions.

The server sends updated character skill totals. The client's skill-tree box
descriptions come from its own `datatables/skill/skills.iff`; matching changes to
that client asset are needed if its preview must show the extra box modifiers.

## Movement

Players move at twice their previous speed, on foot and while riding creature
mounts or ground vehicles. Acceleration is also doubled to preserve the time it
takes to reach full speed. Existing speed buffs, posture restrictions, gallop and
combat slowing still apply. NPC movement and spacecraft flight are unchanged.

The multiplier is applied once to the player, including riders. Mount and vehicle
base speeds are not multiplied again. The server's rider speed checks use the
same multiplier, and player movement is refreshed at login.

## Tumbling

Tumble to Standing, Tumble to Kneeling and Tumble to Prone each consume all
remaining Health, Action and Mind, setting those three current pools to zero.
Secondary stats, maximum HAM and wounds are not changed, and stat-based cost
reductions do not reduce this cost. All three pools must be positive to start a
tumble; failed state, locomotion or HAM checks do not charge anything.

The command plays its tumble animation, cancels pending dizzy falls, updates all
three bars and sends one normal incapacitation notification. This incapacitation
counts toward the normal repeated-incapacitation death rules. Rebuild Core3 and
restart the server to apply it.

## Stimpacks

All stimpack definitions heal Health, Action and Mind damage. The same calculated
healing power applies to each pool, including skill and battle-fatigue modifiers.
This includes ordinary, quest, ranged and area stims, and stims dispensed by a
droid. Area healing also accepts patients who have only Mind damage.

The normal charge consumption, cooldown, skill requirements and Mind cost to use
a stimpack still apply. When healing yourself, that Mind cost is deducted after
the healing, so the net Mind recovery is lower than the healing amount. This
restores damage within the pool's existing wound-adjusted maximum.

Existing items read their healed attributes from the loaded templates, so these
changes apply after a server restart without recreating stimpacks. Deploy the Lua
definitions and rebuild Core3 for the area-target check.

## Travel

Using a travel terminal normally opens the original galaxy/planet travel map.
Starport terminals also offer an **All destinations** option in their right-click
radial menu. That optional list includes all operating starports on every enabled
planet, plus the existing eligible local shuttle destinations. After selecting a
destination, choose a one-way or round-trip ticket and board normally. Use this
option for direct routes that the stock client's map does not expose.

The server permits direct travel between starports, but the original map still
uses the client's travel data. Showing every direct route and the reduced fares
on that map requires a matching client asset update; this server change does not
distribute one. The optional destination list works without a client patch.

Existing fares retain the earlier 100x reduction. Newly opened interplanetary
routes cost 10 credits one way or 20 for a round trip. New routes use a 1,000-credit
authored fare and apply `CreditScale` once at purchase. Quotes and payment messages
use the reduced amount. The ordinary ticket command still handles funds, inventory
space, travel coupons and city bans; it verifies the actual departure terminal.

Disabled planets, destinations with incoming travel disabled and locations
without a shuttle remain unavailable. Local shuttleports continue using the
ordinary planet map and local-travel rules. Its client-supplied base-fare display
may still show the original amount, as noted in `CREDIT_ECONOMY.md`.

## Applying and checking

Rebuild Core3, allowing its IDL generation step to run, deploy the new executable
alongside the current scripts, and restart the server. Existing players receive
their skill and movement updates when they log in. No balance or character-data
migration is needed.

`utils/tests/gameplay_tuning_test.py` compiles the production modifier, skill
reconciliation, fare and route methods, travel terminal handlers and the travel
SUI callback against in-memory game objects. It loads the actual ten-planet Lua configuration and
checks bonuses, repeat-login behavior, movement modifiers, route eligibility,
the default map-opening packet, the optional starport radial entry, ticket
selection, cancellation, invalid selections, distance checks and pricing.

Run from the repository root with Python, `lupa`, and a C++17 compiler:

```sh
python MMOCoreORB/utils/tests/gameplay_tuning_test.py
```

On Windows, use a Visual Studio developer prompt and add `--compiler cl`.
These checks passed, including 1,744 one-way/round-trip menu selections. They do
not replace a full server build or live-client test; this checkout has no populated
`MMOCoreORB/utils/engine3` dependency, so those require the normal build environment.

Run `python MMOCoreORB/utils/tests/stimpack_healing_test.py` with the same
dependencies to check all 27 stimpack and repair-kit definitions and compile the
production area-target and healing methods. It covers Mind-only patients, all
three pools, and the existing line-of-sight, entry and dead-target restrictions.

`python MMOCoreORB/utils/tests/tumble_ham_test.py` compiles all three tumble
commands against an in-memory creature. It checks the full drain with low and
high secondary stats, single incapacitation notification, canceled dizzy falls,
and no HAM changes on rejected commands. It requires Python and a C++17 compiler;
use `--compiler cl` from a Visual Studio developer prompt on Windows.
