# Credit economy

Game-authored credit prices, generated rewards, and credit loot are divided by
100 and rounded up to whole credits. For example, 1,000 becomes 10, 15,000 becomes
150, 530 becomes 6, and a positive amount below 100 becomes 1. Free actions remain
free. XP, faction points, resource quantities, skill requirements, and drop
probabilities are not currency and retain their existing values.

## Covered systems

| System | Conversion point |
| --- | --- |
| Training | After persuasion, before the quote, funds check, and cash/bank split |
| Terminal missions and bounties | Client reward packets and final payment; raw internal rewards still drive generation and bounty XP |
| Theme parks, journal quests, helper droid, theater, crafting contracts | Script reward calculation, with matching payment messages |
| NPC credit loot | Loot generation, before any solo or group distribution |
| Treasure chests and junk dealers | Generated chest reward or each item's resale price |
| Starting credits and character-builder grant | Grant calculation |
| Travel and droid dispatch | Final base fare, including the full round trip before rounding |
| Vehicle and ship repairs, chassis dealer | Final repair or chassis price |
| Cloning, insurance, Flash Speeder replacement | Quote and charge |
| Buildings, vendors, civic structures, city registration/specializations | Upkeep rate or periodic upkeep charge, with matching maintenance reports |
| Bazaar listing fees and bank transfer surcharge | Final fee, after existing discounts/waivers |
| Contraband and reaction fines | New fine assessment |
| NPC drinks, event deeds, information, bribes, quest purchases | Quote, affordability check, and payment |
| Slot machines and Nym's card game | Authored wager/payment and final payout; cumulative slot stakes round once |
| Roulette | Authored limits and payouts; `/bet` continues to accept actual credits |

Existing cash, bank balances, city/vendor/structure deposits, and player-set prices
are not migrated. Bank deposits/withdrawals, player trades, tips, auctions,
building admission, player-set city taxes, image-design payments, lottery pots,
maintenance deposits, and refunds continue moving the exact agreed amount. They
must not apply the reduction again to money already in circulation. Percentage
taxes on reduced game prices naturally follow the reduced price.

## Implementation

C++ uses `src/server/zone/managers/credit/CreditScale.h`; screenplay code uses
`math.ceil(amount / 100)`. Apply the conversion once to an authored or generated
amount before checks, client messages and settlement. Keep authored configuration
values in their original units. Do not reduce the low-level credit add/subtract
methods: they also handle transfers, refunds, and split payments.

Mission objects intentionally store authored rewards. Their baseline and delta
packets convert for display; completion converts the final reward plus any bonus
once. This also handles missions accepted before the update, without altering
mission multipliers or bounty XP. Existing assessed fines and existing upkeep
arrears are already debts and are not automatically rewritten.

## Applying and checking the update

Rebuild Core3 and deploy both the new executable and updated Lua scripts, then
restart the server. A script-only restart does not apply the C++ changes. This
checkout has no populated `engine3` submodule, so a complete server build and live
gameplay test require the normal server build environment.

Server-generated training, mission, vendor, repair, and fee messages use the new
amounts. The stock client also contains its own fixed text and travel-fare data;
its native travel window may still show the original base fare until matching
client assets are updated. Server-side charges use the reduced fare.
Starport terminals now use a server-generated destination and ticket menu with
accurate fares; see `GAMEPLAY_TUNING.md`. Local shuttleports retain the native map.

Run the standalone checks from the repository root:

```sh
c++ -std=c++17 MMOCoreORB/utils/tests/credit_scale_test.cpp -o /tmp/credit_scale_test
/tmp/credit_scale_test
lua MMOCoreORB/utils/tests/credit_economy_test.lua
git diff --check
```

The C++ check covers whole-credit rounding, zero, sentinels, large amounts, and
the rounding bounds for one million inputs. The Lua checks execute production
training methods (quotes, affordability, persuasion, cash/bank splits), theme-park
rewards and messages, and ship-repair quotes/checks with an in-memory game interface.
