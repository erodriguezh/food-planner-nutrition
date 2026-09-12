# Context: food planner and nutrition tracker

Glossary of the domain language for this vault. Terms are defined once here and used with the same meaning everywhere: node files, routines, the index, and conversation.

## Nodes

- **Food**: one edible thing with known macros per 100 g. A Food is generic (`Chicken breast`) or packaged (`Chicken meatballs Spar`). Each Food is one markdown file.
- **Meal**: a named combination of Foods in gram amounts, with stored totals. A Meal exists only when the user names it. Each Meal is one markdown file.
- **Day**: one calendar day of eaten Meals and Foods, with running totals and a summary at close. Plans are never stored on a Day. Each Day is one markdown file named by its date.
- **Goals**: the one fixed daily target for calories, protein, fat and carbs. One markdown file. A change in chat edits it.
- **Pantry**: what is available to eat right now: staples and items. One markdown file. The conversation overrides it.

## Food terms

- **Canonical name**: the English name of a Food. It is the file name and the `name` property. For a packaged product it ends with the brand.
- **Label name**: the product name as printed on the package, often German. Stored in `label_name` and repeated in `aliases`.
- **Alias**: any other name the user says for a Food or a Meal. Stored in `aliases`. Food and Meal aliases share one table. An alias is never a link target; links always use the canonical name.
- **Serving alias**: a named portion that maps to grams, written `<count> <unit> = <grams> g`. The first serving alias is the default portion.
- **Number source**: where the macro numbers came from. One of `label` (read from the package), `database` (a nutrition database lookup), `estimate` (agent estimate from a similar food).
- **Reviewed**: the user looked at the numbers and said ok. Independent of number source: a label read by the agent is unreviewed until the user confirms it.
- **Label basis**: whether the package states values per `100g` or per `100ml`. Stored values are always per 100 g.
- **Density**: grams per millilitre of a liquid Food. Used once, at creation, to convert per-100-ml label values and ml serving aliases to grams. Its origin is recorded with the same vocabulary as number source.
- **Category**: a coarse class of a Food used by rebalance: `protein`, `dairy`, `grain`, `vegetable`, `fruit`, `fat`, `snack`, `drink`.
- **Estimated from**: the Food whose numbers an estimate was copied or scaled from. The only outgoing link a Food holds.

## Meal terms

- **Ingredient**: one Food and its amount in grams inside a Meal, written `[[Canonical name]] = <grams> g`. Ingredients are Foods only; a Meal never contains a Meal.
- **Portion**: one equal share of a Meal. A Meal states how many portions it makes; one portion is the totals divided by that count.
- **Meal weight**: the sum of ingredient grams, raw.
- **Cooked weight**: the weight of the whole Meal after cooking, stored only when the user weighed it. Used to convert cooked grams of a leftover to raw grams. Without it the agent estimates the shrink and states the error.
- **Totals**: the macros of the whole Meal, all ingredients added up: calories, protein, fat, carbs, fiber, sugar, salt.
- **Totals date**: the day the totals were last computed. Totals are recomputed when an ingredient Food changed after that day.
- **Slot**: the place of a Meal in a day. One of `breakfast`, `lunch`, `snack`, `dinner`. A Meal may fit several slots or any slot.
- **New Food**: a Food the user names in chat that has no node yet. The agent creates it as a generic Food with standard values and marks it unreviewed. It asks nothing.
- **Unnamed combination**: Foods logged together without a Meal name. Recorded on the Day only; it never becomes a Meal.

## Day terms

- **Entry**: one thing eaten on a Day: a Meal by portion or by weight, or a Food by weight, with its macros. Written as one line under a slot heading.
- **Ingredient change**: a Meal entry where one ingredient amount differs from the Meal node. Recorded on the entry, never on the Meal.
- **Running totals**: the seven totals (calories, protein, fat, carbs, fiber, sugar, salt) of everything eaten so far on a Day. Rewritten on every log.
- **Remaining**: goal minus running totals. What is left to eat today. The basis for rebalance.
- **Status**: the state of a Day. `open` (logs still come), `closed` (the user closed the day), `auto-closed` (a log for a later date closed it).
- **Close the day**: the user's request that ends a Day. Writes the status and the summary.
- **Auto-close**: a log whose date is later than the last open Day closes that Day and opens a new one.
- **Summary**: the text written at close: totals per slot, the goal used, over or under per macro, and the verdict.
- **Verdict**: fixed words at close. `on target` when all four macros are inside their range; otherwise `off target:` followed by each macro that is off and its direction (`low` or `high`).
- **Open slot**: a slot with no entry on the Day. Open slots are counted in the fixed slot order. The user can remove one in chat ("no snack today").
- **Next slot**: the first open slot in order. The one slot a suggestion covers in full.
- **Rebalance**: the act of computing what is left today and, on request, suggesting the next slot. Works from numbers only; there is no stored plan.
- **Suggestion**: the agent's proposal for the next slot: Foods or Meals, amounts, macros, plus one rough line for the later open slots. Made only when the user asks.
- **Plan**: a suggestion of what to eat, made in the chat. It is never written to the vault.

## Goals terms

- **Target**: one daily number for calories, protein, fat or carbs. There are four targets and no variants per day type.
- **Range**: the min and max stored per macro, computed from the target and the tolerance when the goal is set. Under min or over max is not an error; the agent states it and the user decides.
- **Tolerance**: one percent applied to every target to build its range. Default 5.
- **Goal change**: the user states a new target in chat. Range and tolerance are rewritten with it. The Goals node is edited; git keeps the old values. Each closed Day summary records the targets it used.

## Pantry terms

- **Staple**: a Food that is always available. Listed by name only, no amount, no expiry. The agent never asks about it. The user says in chat when it runs out.
- **Item**: a Food or a Meal that runs out or expires. Listed with an optional rough amount and an optional expiry date.
- **Amount**: the rough quantity of an item. Foods in grams; Meals in portions or cooked grams. Never exact. Logging never changes it.
- **Expiry**: the `until` date of an item. Set only when the user states it. Items near expiry get priority at plan time.
- **Leftover**: a cooked Meal kept as a Pantry item, in portions or cooked grams, with an optional expiry.
- **Restock**: the user says they went shopping and adds photos of the receipt, the shopping list, or the bought items. The agent proposes the items to add and appends them after the user's ok.

## Units

- **Gram** is the only stored unit for amounts. The user may log grams, servings, or millilitres; the agent converts to grams before anything is written.
