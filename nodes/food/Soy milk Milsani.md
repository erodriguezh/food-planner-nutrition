---
type: food
name: Soy milk Milsani
aliases:
  - Sojadrink Milsani
  - Milsani soja
category: drink
brand: Milsani
kcal_per_100g: 43
protein_g_per_100g: 3.1
fat_g_per_100g: 1.7
carbs_g_per_100g: 3.7
fiber_g_per_100g: 0.5
sugar_g_per_100g: 3
salt_g_per_100g: 0.1
label_basis: 100ml
density_g_per_ml: 1.0
density_source: estimate
number_source: database
source_ref: https://world.openfoodfacts.org/product/24008853
source_date: 2026-09-15
reviewed: false
---

## Notes

Aldi own brand, plain soy drink. The lookup ran in the order of
`routines/create-food.md` step 5. Open Food Facts holds six of the seven
numbers but no fiber. The Swiss Food Composition Database returned no usable
answer, so fiber comes from USDA FoodData Central 175215, soymilk unsweetened,
0.5 g per 100 g. Values are per 100 ml converted with density 1.0.

No label photo arrived, so no `barcode` is stored: the Open Food Facts entry
is the Milsani plain soy drink, but the owner's exact package is unconfirmed.
Also no `servings`: the owner has not stated a portion. Both follow once the
owner shows the package.
