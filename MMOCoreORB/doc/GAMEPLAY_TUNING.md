# Master skills, movement and direct travel

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
