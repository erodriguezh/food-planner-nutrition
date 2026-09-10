# Research: nutrition databases for on-the-fly lookups

Ticket: https://github.com/erodriguezh/food-planner-nutrition/issues/13
Date of research: 2026-09-10. All live API calls below ran on that date.

## Summary

- Recommended lookup order: (1) Open Food Facts for any packaged product or barcode, (2) Swiss Food Composition Database API for fresh and generic foods with a German name, (3) USDA FoodData Central (Foundation / SR Legacy) for generic foods that the Swiss database lacks, (4) manual estimate from a similar food, marked as an estimate.
- Open Food Facts needs no key for reads. It needs a custom `User-Agent`. It supports barcode lookup. Rate limit: 15 product reads/min and 10 searches/min per IP. Licence ODbL/DbCL with attribution. The Austrian site lists 22,722 products. Data quality varies per product.
- The Swiss Food Composition Database API is free, open, and unauthenticated. It returns generic foods in German per 100 g edible portion (1,246 foods, V 7.1). It has no barcode lookup and no branded Austrian products. Attribution to the source is required.
- USDA FoodData Central needs a free data.gov API key on every request. `DEMO_KEY` works for tests only. Data is CC0 (public domain). It has the best analytical data for generic fresh foods, but only English names. Branded foods cover the United States and New Zealand only, so Austrian barcodes return nothing.
- German BLS 4.0 is CC BY 4.0 and free, but it is an Excel download with no public API. ÖNWT (Austria) is a paid dataset with a web search UI only. EFSA's food composition data is a dashboard and Excel export, not an API, and does not list Austria.
- A chat-app agent can call Open Food Facts and the Swiss API with a plain unauthenticated GET. USDA needs a key in the URL, so store a personal key in the vault or use `DEMO_KEY` for very low volume.
- Fallback when nothing is found: use the closest generic food from the Swiss or USDA database, write the source and the word "estimate" in the entry, and ask the user to scan the label later.

## Comparison table

| Criterion | Open Food Facts | USDA FoodData Central | Swiss Food Composition Database (FSVO) | German BLS 4.0 (MRI) | ÖNWT (Austria) | EFSA EU FCDB |
|---|---|---|---|---|---|---|
| API access | REST, `/api/v2/product/{barcode}`, `/api/v2/search`, legacy `/cgi/search.pl` full-text [1][3] | REST, `/v1/food/{fdcId}`, `/v1/foods/search`, `/v1/foods/list` [4] | REST JSON, `.../BLV-api/foods`, `.../BLV-api/values` [8][9] | No API. Excel download `BLS_4_0_Daten_2025_DE.xlsx` [12][13] | No API. Web search UI and paid data packages [14][15] | No API. MicroStrategy dashboard and Excel dataset [17][18] |
| Auth / key | "READ operations ... do not require authentication other than the custom User-Agent" [1] | "a data.gov API key must be incorporated into each API request"; `DEMO_KEY` for tests [4]. Live test without key: HTTP 403 | "API is free to use and allows unrestricted access" [8]. Live test: no key needed | Not applicable (download) | Not applicable | Not applicable |
| Licence | Database ODbL, contents DbCL, images CC BY-SA [2] | "in the public domain" under "CC0 1.0 Universal" [4] | Free, commercial use allowed "subject to acknowledgment of the source" [6][7] | CC BY 4.0 [12] | Purchase model: "Der Kauf von Daten beinhaltet Updates ... für sechs Monate" [15]. Licence text not found | Dataset on Zenodo: CC BY 4.0 [18] |
| Attribution | "mention the licence and to attribute the authorship to Open Food Facts with a link to https://openfoodfacts.org" [2] | Suggested citation: "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, 2019. fdc.nal.usda.gov." [4] | Acknowledge the source (FSVO) [7] | "Max Rubner-Institut (2025): Bundeslebensmittelschlüssel (BLS), Version 4.0 - Deutsche Nährstoffdatenbank." [13] | Not stated | Credit the creator (CC BY) [18] |
| Austrian supermarket products | Yes, crowd-sourced. at.openfoodfacts.org shows "22.722 Produkte" [5]. Live test: `clever` Kulturheidelbeeren (barcode 9010437044301) found with `countries_tags` `en:austria` | No. "Market countries in the GBFPD currently include United States and New Zealand" [11]. Live test for `Manner Schnitten` and an Austrian GTIN: no relevant hits | No branded products; foods "available in Switzerland", generic [8] | Generic foods only, 7,140 items [12] | Yes by design: brand and retail products, "more than 10,000 datasets", D-A-CH region [14]. Not reachable by API | No |
| Fresh / generic foods | Weak. Fresh produce appears only as packaged items with a label | Strong. Foundation and SR Legacy; "All reported values are based on a 100-gram or percent basis of the edible portion" [10] | Strong for German names. 1,246 foods, "Heidelbeere, roh" found [6][9] | Strong, 7,140 foods, 138 nutrients [12] | Strong (includes BLS data) [14] | Micronutrient focus; 2013 dataset has no energy or macros [18] |
| Fields per 100 g | `nutriments.energy-kcal_100g`, `proteins_100g`, `fat_100g`, `carbohydrates_100g`; `nutrition_data_per` [3] and live test | `foodNutrients[]` with `nutrientName`, `unitName`, `value` (or `number`, `name`, `amount` in abridged format). Nutrient numbers 208 kcal, 203 protein, 204 fat, 205 carbohydrate (live test) | `values[]` with `component.code` `ENERCC` (kcal), `PROT625` (protein), `FAT` (fat), `CHO` (available carbohydrate), `unit`, `value`; "All data refer to 100 g edible portion" [9][20] | 138 nutrients per 100 g in Excel [12] | 131 nutrients per entry [14] | Excel columns, micronutrients [18] |
| Barcode lookup | Yes, `GET /api/v2/product/{barcode}` [3] | Only by text search over `gtinUpc` for US/NZ products [4][11]; Austrian GTIN not found in live test | No | No | No | No |
| Rate limits | "15 req/min/IP address for all read product queries", "10 req/min/IP address for all search queries" [1] | "1,000 requests per hour per IP address"; `DEMO_KEY` "30 requests per IP address per hour" and "50 ... per day" [4]. Live header showed `x-ratelimit-limit: 10` with `DEMO_KEY` | Not stated; "unrestricted access" [8] | Not applicable | Not applicable | Not applicable |
| Plain unauthenticated GET from a chat app | Yes, with `User-Agent` header. Note: some chat fetch tools cannot set a custom header; see Unverified | Yes for the HTTP call, but the key must be in the URL (`api_key=`) | Yes | No | No | No |
| Languages | Product names as printed; German for Austrian products (live test) | English only. Search `Heidelbeeren`: 0 hits (live test) | `lang=de`, `en`, `fr`, `it` [6][9] | German | German, some English | English |

## Example requests and response fields

### Open Food Facts (top source for packaged products)

Barcode lookup (live test, 2026-09-10):

```
GET https://world.openfoodfacts.org/api/v2/product/9010437044301?fields=code,product_name,brands,countries_tags,nutriments.energy-kcal_100g,nutriments.proteins_100g,nutriments.fat_100g,nutriments.carbohydrates_100g,nutrition_data_per
User-Agent: food-planner-nutrition/0.1 (contact email)
```

Response (trimmed):

```json
{
  "code": "9010437044301",
  "status": 1,
  "status_verbose": "product found",
  "product": {
    "product_name": "Kultuheidelbeeren",
    "brands": "clever",
    "countries_tags": ["en:austria", "en:germany"],
    "nutrition_data_per": "100g",
    "nutriments": {
      "energy-kcal_100g": 40,
      "proteins_100g": 0.87,
      "fat_100g": 0.33,
      "carbohydrates_100g": 10.6
    }
  }
}
```

A missing product returns `"status": 0, "status_verbose": "product not found"` (live test with barcode 9000331311100).

Text search (legacy endpoint, live test):

```
GET https://world.openfoodfacts.org/cgi/search.pl?search_terms=Heidelbeeren&countries_tags=en:austria&json=1&page_size=3&fields=code,product_name,brands,nutriments.energy-kcal_100g,nutriments.proteins_100g,nutriments.fat_100g,nutriments.carbohydrates_100g
```

Response fields: `count`, `page`, `page_count`, `products[]` with the same fields as above. The docs say full-text search "is not available in the v2 or v3 server-side API" and `/cgi/search.pl` is "not recommended for new integrations" [3]. On the test date, `/api/v2/search` returned HTTP 503 "Page temporarily unavailable", while `/cgi/search.pl` and `/api/v2/product/` worked.

Agent rules for this source:

- Always send a `User-Agent` in the form `AppName/Version (ContactEmail)` [1].
- Stay under 15 product reads and 10 searches per minute [1].
- Check `nutrition_data_per`. Some products store values per serving.
- Some `nutriments` fields can be missing. Fall back to the next source when `energy-kcal_100g` is absent.

### Swiss Food Composition Database API (top source for fresh and generic foods)

Search by German name (live test):

```
GET https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/BLV-api/foods?search=Heidelbeere&lang=de&limit=3
```

Response (trimmed):

```json
[
  {"id": 351433, "foodName": "Heidelbeere, gefriergetrocknet", "generic": true, "categoryNames": "Früchte getrocknet", "foodid": 14101},
  {"id": 351513, "foodName": "Heidelbeere, roh", "generic": true, "categoryNames": "Früchte frisch", "foodid": 389}
]
```

Values for one food (`DBID` = `id` from the search):

```
GET https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/BLV-api/values?DBID=351513&lang=de
```

Response (trimmed to the four macros; the full list has about 45 components):

```json
[
  {"component": {"code": "ENERCC", "name": "Energie, Kalorien"}, "value": "51.0", "unit": "kcal"},
  {"component": {"code": "PROT625", "name": "Protein"}, "value": "0.9", "unit": "g"},
  {"component": {"code": "FAT", "name": "Fett, total"}, "value": "0.2", "unit": "g"},
  {"component": {"code": "CHO", "name": "Kohlenhydrate, verfügbar"}, "value": "10.6", "unit": "g"}
]
```

Notes:

- `value` is a string. Convert it to a number.
- All values refer to 100 g edible portion [20].
- `GET .../BLV-api/versiondb` returned `{"idversion":51,"versiontext":"V 7.1"}`.
- OpenAPI spec: https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/openapi.json [8].

### USDA FoodData Central (third source)

```
GET https://api.nal.usda.gov/fdc/v1/foods/search?api_key=YOUR_KEY&query=blueberries%20raw&dataType=Foundation,SR%20Legacy&pageSize=1
GET https://api.nal.usda.gov/fdc/v1/food/2346411?api_key=YOUR_KEY&format=abridged
```

Abridged response fields (live test, fdcId 2346411 "Blueberries, raw"): `foodNutrients[]` with `number`, `name`, `amount`, `unitName`. Values: Energy (Atwater General Factors) 63.9 kcal, Protein 0.703 g, Total lipid (fat) 0.306 g, Carbohydrate, by difference 14.6 g. Search responses use `nutrientName`, `unitName`, `value`, `nutrientNumber` instead.

## Recommended lookup order and fallback

1. If the user gives a barcode or a branded product name: query Open Food Facts. Use the barcode endpoint first, then `search.pl` with `countries_tags=en:austria`.
2. If the food is fresh or generic (for example "Heidelbeeren", "Topfen"): query the Swiss API with `lang=de`. Prefer the entry with `generic: true` and the matching preparation ("roh").
3. If the Swiss API has no match: translate the name to English and query USDA with `dataType=Foundation,SR Legacy`. Store the personal API key in the vault. `DEMO_KEY` allows very few calls.
4. If nothing matches: pick the closest generic food in the Swiss or USDA database, record the value with the tag `estimate` and the source URL, and ask the user to scan the label when possible.

Record the source name and URL with every stored value. Open Food Facts requires a licence mention and a link; USDA requests a citation; the Swiss FSVO requires acknowledgment.

## Unverified

- Whether the chat-app fetch tools in claude.ai and ChatGPT can set a custom `User-Agent` header. Open Food Facts asks for one to avoid bot detection [1]. Claude Code can (`curl -A`). A test from each chat app is still open.
- Whether ÖNWT offers any machine-readable access or an API. The public pages show a web search UI and paid data packages only [14][15][16]. Contact: nuts@dato.at [16].
- The current EFSA "Food composition data 2026" content, countries, and licence. The page is a JavaScript dashboard and did not render for the fetch tool [17]. Only the 2013 dataset on Zenodo was checked [18].
- The exact BLS 4.0 licence document. The download page states CC BY 4.0 [12]; the licence page links a ZIP for the older 3.0X terms [19].
- Swiss API rate limits. The documentation says "unrestricted access" [8] but gives no number.
- The USDA `DEMO_KEY` hourly limit. Docs say 30/hour [4]; the live response header showed `x-ratelimit-limit: 10`.
- Whether `/api/v2/search` on Open Food Facts is stable. It returned HTTP 503 on the test date, while the product endpoint and `search.pl` worked.
- The Open Food Facts count of 22,722 Austrian products is a homepage counter [5], not an API result.

## Sources

1. Open Food Facts API introduction (auth, User-Agent, rate limits, licences): https://openfoodfacts.github.io/openfoodfacts-server/api/
2. Open Food Facts terms of use (ODbL, DbCL, CC BY-SA, attribution): https://world.openfoodfacts.org/terms-of-use
3. Open Food Facts API cheat sheet (product endpoint, fields, search): https://openfoodfacts.github.io/openfoodfacts-server/api/ref-cheatsheet/ and tutorial https://openfoodfacts.github.io/openfoodfacts-server/api/tutorial-off-api/
4. USDA FoodData Central API guide (key, rate limits, endpoints, CC0, citation): https://fdc.nal.usda.gov/api-guide/
5. Open Food Facts Austria homepage (product count): https://at.openfoodfacts.org/
6. Swiss Food Composition Database homepage (FSVO, V 7.1, 1,246 foods, languages, terms): https://www.naehrwertdaten.ch/en/
7. Swiss Food Composition Database downloads (free, commercial use, acknowledgment, API description link): https://www.naehrwertdaten.ch/en/downloads/
8. Swiss Food Composition Database API description (docx): https://naehrwertdaten.ch/wp-content/uploads/2025/07/The-Swiss-Food-Composition-Database-API-descripton_V3-separate-API-prod.docx ; OpenAPI: https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/openapi.json
9. Swiss API base URL (live tests): https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/BLV-api
10. USDA Foundation Foods documentation (per 100 g edible portion): https://fdc.nal.usda.gov/Foundation_Foods_Documentation/
11. USDA Global Branded Food Products Database documentation (US and New Zealand, 100-unit basis): https://fdc.nal.usda.gov/GBFPD_Documentation/
12. BLS 4.0 homepage and download (7,140 foods, 138 nutrients, CC BY 4.0, Excel): https://blsdb.de/ and https://blsdb.de/download
13. BLS FAQ (file name, cost, citation): https://blsdb.de/faq
14. ÖNWT homepage (10,000+ datasets, 131 nutrients, brand products, University of Vienna): https://www.oenwt.at/ and https://www.oenwt.at/content/english-version/
15. ÖNWT data packages (purchase model): https://www.oenwt.at/content/oenwt-datenpakete/
16. ÖNWT use and liability: https://www.oenwt.at/content/naehrwert-suche/nutzung-und-haftung/
17. EFSA food composition data (16 national databases, 2013 and 2026 dashboards): https://www.efsa.europa.eu/en/data-report/food-composition-data and https://www.efsa.europa.eu/en/microstrategy/food-composition-data-2026
18. EFSA 2013 food composition dataset on Zenodo (CC BY 4.0, seven countries, micronutrients): https://zenodo.org/records/438313
19. BLS licence page: https://blsdb.de/license
20. Swiss Food Composition Database, interpretation of data (100 g edible portion): https://naehrwertdaten.ch/en/interpretation-of-food-composition-data/
21. USDA FoodData Central data type documentation index: https://fdc.nal.usda.gov/data-documentation/
