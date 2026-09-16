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
- **Lookup order**: the fixed order of sources for missing or generic numbers: Open Food Facts, Swiss Food Composition Database, USDA FoodData Central, then an estimate from a similar Food. The reply names the source used.
- **Alias table**: the Food and Meal lines of the Index read as one table: canonical name, category or slots, aliases plus label name. The agent resolves every name said in chat against it without opening nodes.
- **Alias resolution**: how a name said in chat becomes one canonical name: exact name, then alias, then one fuzzy hit, all case-insensitive and tolerant of umlauts and plurals. Several hits of one kind: the Pantry one wins, else the agent asks. A Food and a Meal together in the one matching stage always ask; the Pantry never decides that collision. The first matching stage stops the search, so an exact name of one kind beats an alias of the other kind. A label photo never asks: its identity decides alone. The barcode, else the label name run against the Foods only with the same exact, alias and fuzzy stages, and the brand then filters the Foods the stage found: the printed brand and the brand the Food carries must agree both ways. Exactly one Food left is reused; zero or several, an ambiguous name included, make a new Food whose name ends with the brand. Pantry membership is not package identity, so it never breaks a label tie.
- **Package identity**: what a label photo alone says the product is: the `barcode`, the printed `label_name` and the printed `brand`. It decides whether a label overwrites an existing Food, and nothing else does; the Pantry is not part of it.
- **Ok step**: the user's "ok" after a create or restock reply. On a Food it sets `reviewed: true` and nothing else. On a restock it writes the shown list. A corrected number is written instead of the ok.

## Meal terms

- **Ingredient**: one Food and its amount in grams inside a Meal, written `[[Canonical name]] = <grams> g`. Ingredients are Foods only; a Meal never contains a Meal.
- **Portion**: one equal share of a Meal. A Meal states how many portions it makes; one portion is the totals divided by that count.
- **Meal weight**: the sum of ingredient grams, raw.
- **Cooked weight**: the weight of the whole Meal after cooking, stored only when the user weighed it. Used to convert cooked grams of a leftover to raw grams. Without it the agent estimates the shrink and states the error.
- **Totals**: the macros of the whole Meal, all ingredients added up: calories, protein, fat, carbs, fiber, sugar, salt.
- **Totals date**: the day the totals were last computed. Totals are recomputed when an ingredient Food changed after that day.
- **Slot**: the place of a Meal in a day. One of `breakfast`, `lunch`, `snack`, `dinner`, in that fixed order. A Meal may fit several slots or any slot. At log time the user's word picks the slot; else the clock, in the bands `routines/log.md` step 3 states; if that slot already has an entry from an earlier message, the next slot in order.
- **Slot word**: one of the four slot names said in a log ("breakfast: usual"). It picks the slot before the clock, and it makes the Meal win a Food-versus-Meal collision in alias resolution.
- **New Food**: a Food the user names in chat that has no node yet. The agent creates it as a generic Food with standard values and marks it unreviewed. It asks nothing.
- **Unnamed combination**: Foods logged together without a Meal name. Recorded on the Day only; it never becomes a Meal.

## Day terms

- **Entry**: one thing eaten on a Day: a Meal by portion or by weight, or a Food by weight, with its macros. Written as one line under a slot heading.
- **Entry line**: the canonical line of an entry: `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`, with `- ~ ` for an estimated input and `, [[Food]] = <n> g` after the amount for an ingredient change. The four macros are whole numbers computed from the node at write time.
- **Ingredient change**: a Meal entry by portion where one ingredient amount differs from the Meal node. Recorded on the entry line, never on the Meal.
- **Guessed amount**: an amount the agent chose because the user did not state one. It puts the estimation mark on the entry line.
- **Estimation mark**: the `~` right after the bullet of an entry line, written when the Food is an estimate, the Meal is estimated or the amount is guessed. On a closed or auto-closed Day the mark is history and stays as written when a node changes later; the canonical shape of the line is still checked there. It bubbles to the Day `estimated` checkbox, the chat totals, the Summary and the weekly average. Nowhere else on a line has meaning.
- **Month line**: the one Index line per Day month, `- <YYYY-MM> | nodes/day/<YYYY-MM>/`, added at the first log of the month.
- **Running totals**: the seven totals (calories, protein, fat, carbs, fiber, sugar, salt) of everything eaten so far on a Day. Rewritten on every log.
- **Remaining**: goal minus running totals. What is left to eat today. The basis for rebalance.
- **Status**: the state of a Day. `open` (logs still come), `closed` (the user closed the day), `auto-closed` (a log for a later date closed it).
- **Close the day**: the user's request that ends a Day. Writes the status and the summary.
- **Auto-close**: a log whose date is later than the last open Day closes that Day and opens a new one.
- **Summary**: the `## Summary` section written at close, in a fixed order: the slot table with one row per slot with an entry and a TOTAL row, the goal line with the targets used and the range each was judged against, one bullet per macro with its amount over or under the target, the verdict, and at most one hint. Every table number carries the estimation mark when the Day is estimated. A log into a closed Day rewrites it, after the entry and the Day totals.
- **Verdict**: fixed words at close, one line of the Summary. `on target` when all four macros are inside the range the goal line stores for them; otherwise `off target:` followed by each macro that is off and its direction (`low` or `high`), comma separated, each macro at most once and in the column order. The macro words are `kcal`, `protein`, `fat`, `carbs`.
- **Macro bullet**: one Summary line per macro, `- <macro> <n> over|under`, the day's total against the target used. Four per Summary, in the column order. The gap carries no sign, and it carries a decimal only when the target does. A macro that hits its target exactly writes `0 under`; `0 over` is not a shape.
- **Hint**: the one optional last line of the Summary, `Hint: ...`, a pointer for tomorrow. Written only when useful; never an open item.
- **Open slot**: a slot with no entry on the Day. Open slots are counted in the fixed slot order. The user can remove one in chat ("no snack today").
- **Next slot**: the first open slot in order. The one slot a suggestion covers in full.
- **Rebalance**: the act of computing what is left today and, on request, suggesting the next slot. Works from numbers only; there is no stored plan.
- **Suggestion**: the agent's proposal for the next slot: Foods or Meals, amounts, macros, plus one rough line for the later open slots. Made only when the user asks. How much of the remaining protein a slot takes is agent judgment unless the user says otherwise.
- **Plan**: the suggestion for all open slots in full, made in the chat before the first log of the day. It is never written to the vault. "No snack today" is part of the plan: it removes a slot in the chat and writes nothing.

## Goals terms

- **Target**: one daily number for calories, protein, fat or carbs. There are four targets and no variants per day type.
- **Range**: the min and max stored per macro, computed from the target and the tolerance when the goal is set. Under min or over max is not an error; the agent states it and the user decides.
- **Tolerance**: one percent applied to every target to build its range. Default 5.
- **Goal change**: the user states a new target in chat. Range and tolerance are rewritten with it. The Goals node is edited; git keeps the old values. Each closed Day summary records the targets and the ranges it used, and a refresh of that Day reuses them.
- **Bound**: one end of a range, stored as `<macro>_min` or `<macro>_max`. Eight bounds per Goals node.
- **Rounding rule**: how a computed number becomes the stored one. Goals bounds: whole number, a half rounds up, stated in `routines/goals.md` step 4. Food numbers: one decimal, a half rounds up, stated in `routines/create-food.md` step 3. Entry line macros and the kcal, protein, fat and carbs totals of a Meal or Day: whole number, a half rounds up; their fiber, sugar and salt: one decimal; stated in `routines/log.md` step 4. The lint applies all three rules; it reads the stored numbers as decimals and scales, divides and sums them as decimals, so a half the arithmetic itself produces still rounds up.

## Pantry terms

- **Staple**: a Food that is always available. Listed by name only, no amount, no expiry. The agent never asks about it. The user says in chat when it runs out.
- **Item**: a Food or a Meal that runs out or expires. Listed with an optional rough amount and an optional expiry date.
- **Amount**: the rough quantity of an item. Foods in grams; Meals in portions or cooked grams. Never exact. Logging never changes it; a log of more than the recorded amount only makes the agent ask "was that the last of X?".
- **Expiry**: the `until` date of an item. Set only when the user states it. Items near expiry get priority at plan time.
- **Leftover**: a cooked Meal kept as a Pantry item, in portions or cooked grams, with an optional expiry.
- **Restock**: the user says they went shopping and adds photos of the receipt, the shopping list, or the bought items. The agent proposes the items to add and appends them after the user's ok.
- **Expired item**: an item whose `until` date is today or past. Flagged in the pantry reply and suggested first at plan time.

## Review terms

- **Review**: the agent's look-back over one calendar week, computed in chat from closed Days only. Nothing is stored. Started by meaning ("how was my week", "last week", "review"), never by a fixed phrase.
- **Week**: Monday to Sunday. "This week" is the current week so far; "last week" is the previous full week. There is no rolling window.
- **Days covered**: how many of the eligible dates have a closed Day, and how many of those were auto-closed. Eligible dates are Monday to today for the current week and all of a past week; a date still to come is not one. A missing day is an eligible date with no Day node at all; missing days are stated, never guessed and never counted as off target. The week's open Day is not counted and not missing; the review names its date in one line.
- **Weekly average**: the per-day mean of each of the seven totals over the closed Days, shown against the target.
- **Days on target**: how many counted Days carry the verdict `on target`.
- **Most common miss**: the macro and direction that appear most often in the week's verdicts, with the day count. A tie names each.

## Units

- **Gram** is the only stored unit for amounts. The user may log grams, servings, or millilitres; the agent converts to grams before anything is written.

## Vault terms

- **Router**: the one file the agent reads first in every session. Pointers and hard rules only, under 500 tokens.
- **Index**: the one file with one index line per node and one line per Day month. The agent updates it at the same time as the node. Retrieval scores the index without opening nodes.
- **Index line**: one line in the index: the link to a node, its category (Food) or slots (Meal), and its aliases. Goals, Pantry and Day-month lines are pointers only.
- **State**: the one file that survives between sessions. Holds the open Day and the open items. Never holds a plan.
- **Write path**: how an app puts a change on `main`. Git for Claude Code; `push_files` on GitHub's remote MCP server for chat apps. The routine text is the same for every app.
- **Open item**: a small pending thing the user still has to settle, listed in the state, for example a Meal without cooked weight. Unreviewed Foods are never open items; the agent mentions them at create time and at close of the day.
- **Routine**: one file that tells the agent how to run one job: log, rebalance, close the day, create food, create meal, pantry, goals, review. A routine holds the method only; it never stores a result.
- **Spec**: the documents that describe the vault for the build session. Not read in daily use.
- **Context MCP**: the planned read-only retrieval service with one tool, `build_context(question)`. When connected, the agent calls it first instead of reading the Index. The vault works without it.
- **Lint**: the script `lint/vault_lint.py` that checks every node, the Index, the State, the Router and the routines against the schemas. Runs locally, by hand or from the pre-commit hook in `.githooks/`. No model involved.
