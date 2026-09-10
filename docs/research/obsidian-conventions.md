# Research: Obsidian properties and links for machine-readable nodes

Ticket: https://github.com/erodriguezh/food-planner-nutrition/issues/15
Date: 2026-09-10
Sources: Obsidian Help (obsidian.md/help), Obsidian Developer Docs (docs.obsidian.md), YAML 1.2.2 spec. Note: `help.obsidian.md` now redirects (301) to `obsidian.md/help`; all citations use the new host.

## Summary

- Obsidian properties are YAML frontmatter between `---` markers. Core types: Text, List, Number, Checkbox, Date (`YYYY-MM-DD`), Date & time (`YYYY-MM-DDTHH:mm:ss`), and Tags (only for `tags`). One type per property name across the whole vault.
- `tags`, `aliases`, `cssclasses` are the default (reserved) list properties. `tag`, `alias`, `cssclass` are deprecated since v1.9. Publish reserves `publish`, `permalink`, `description`, `image`, `cover`.
- Nested YAML objects are not supported in the Properties UI. Obsidian says "use source mode" for them. Markdown inside properties is not rendered by design. Keep every value flat: scalar or list of scalars.
- Wikilink forms: `[[note]]`, `[[folder/note]]`, `[[note|display]]`, `[[note#heading]]`, `[[note#sub#subsub]]`, `[[note#^block-id]]`. Block ids allow only Latin letters, numbers, dashes. Alias links are written as `[[Note|Alias]]`, never as `[[Alias]]`.
- The "New link format" setting (Shortest path when possible / Relative / Absolute) controls how Obsidian writes new links. Resolution of ambiguous short names is not documented on the help site; the API exposes `getFirstLinkpathDest(linkpath, sourcePath)` as "the best match".
- File names: the help site only says Obsidian respects OS limits. The characters `[ ] # ^ |` break link syntax and `\ / :` break file systems. The exact block list is not on the official site (see Unverified).
- `key:: value` inline fields are Dataview-only. The Obsidian syntax page does not mention `::`.
- Daily notes creates one file per day named by a moment.js format (default `YYYY-MM-DD`), supports folders in the format and a template file. Templates supports `{{title}}`, `{{date}}`, `{{time}}` with format overrides.
- Recommendation: use one file per node, flat frontmatter, strings for anything with units or `=`, links quoted as `"[[...]]"`, and a `type` text property for the node kind.

## Findings

### Q1. Properties (frontmatter)

**Format.** "Properties are stored in YAML format at the top of the file." Each entry is `name: value` between `---` lines. "While the order of each name-value pair doesn't matter, each name must be unique within a note." Obsidian also reads a JSON object between the `---` lines, but "the JSON block will be read, interpreted, and saved as YAML." Source: https://obsidian.md/help/properties

**Types.** The Properties UI lists: Text, List, Number, Checkbox, Date, Date & time, Tags. Source: https://obsidian.md/help/properties

| Type | Official rule (verbatim or near-verbatim) |
|---|---|
| Text | "Text properties contain a single line of text. Markdown formatting is not rendered in text properties." Internal links in text properties "must be surrounded with quotes". |
| List | "List properties contain multiple values. Each value in a list appears on its own line, preceded by a hyphen (-) and a space." Links in lists must be quoted too. |
| Number | "Number type properties must always be a literal number, not an expression with operators. Integers and decimals are both allowed." |
| Checkbox | "Checkbox properties are either `true` or `false`." An empty value counts as false. |
| Date | Stored as `YYYY-MM-DD`. With Daily notes enabled, "the date property will additionally function as an internal link to the corresponding daily note for that date." |
| Date & time | Stored as `YYYY-MM-DDTHH:mm:ss` (example `2020-08-21T10:30:00`). |
| Tags | Only for `tags`: "This property type cannot be assigned to other properties." |

**Vault-wide type.** "Once a property type is assigned to a property name, all properties with that name across your vault will use the same type." Consequence for this vault: do not reuse a name such as `source` as text in Food and as list in Pantry. Source: https://obsidian.md/help/properties

**Default (reserved) properties.** `tags` (List), `aliases` (List), `cssclasses` (List). Publish: `publish`, `permalink`, `description`, `image`, `cover`. Deprecated as of v1.9: `tag`, `alias`, `cssclass`. Source: https://obsidian.md/help/properties

**`aliases` behaviour.** "Aliases should always be formatted as a list in YAML." In link autocomplete "any alias shows up in the list of suggestions, with a curved arrow icon next to it." When you pick an alias, "Obsidian uses the `[[Artificial Intelligence|AI]]` link format" so the target stays the real file name. Backlinks can find "unlinked mentions" of aliases. Source: https://obsidian.md/help/aliases

**`tags` behaviour.** "Tags in YAML should always be formatted as a list" and the example omits the `#`. Tag rules: letters, numbers, `_`, `-`, `/` for nesting, "commonly accepted Unicode characters, including emojis"; no spaces; "Tags must contain at least one non-numerical character"; "Tags are case-insensitive". Source: https://obsidian.md/help/tags

**Nested objects and non-standard types.** The help page lists "Nested properties" under features "not currently supported" and says "To view nested properties, we recommend using the source mode." Markdown in properties is "an intentional limitation as properties are meant for small, atomic bits of information that are both human and machine readable." The page does not describe how the UI renders a nested object or an invalid YAML file (see Unverified). Source: https://obsidian.md/help/properties

**Developer view.** The metadata cache exposes `frontmatter: FrontMatterCache`, `frontmatterLinks: FrontmatterLinkCache[]` (since 1.4.0, each with `key`, `link`, `original`, `displayText`), `frontmatterPosition`, plus `links`, `headings`, `tags`, `blocks`, `sections`, `listItems`. This confirms that Obsidian indexes quoted `"[[...]]"` values in frontmatter as links. Sources: https://docs.obsidian.md/Reference/TypeScript+API/CachedMetadata, https://docs.obsidian.md/Reference/TypeScript+API/FrontmatterLinkCache. `FileManager.processFrontMatter` reads, mutates and saves frontmatter "atomically" as a JS object and may throw `YAMLParseError`. Source: https://docs.obsidian.md/Reference/TypeScript+API/FileManager/processFrontMatter

**YAML quoting rules relevant to the index builder.** A plain scalar cannot contain `: ` (colon space) or ` #` (space hash), and cannot start with `* & ! % @ \` [ {`. Use double quotes for escapes, single quotes otherwise. Empty value or `~` is null. `---` marks document start. Source: https://yaml.org/spec/1.2.2/ (chapters 6-7, 9). Practical consequence: a value like `1 meatball = 30 g` is safe as a plain scalar, but `Fett: 12 g` or `#hash` must be quoted.

### Q2. Wikilink forms and resolution

Forms documented on https://obsidian.md/help/links:

- `[[Three laws of motion]]` and `[[Three laws of motion.md]]` (extension optional)
- `[[Projects/Three laws of motion]]`: "To link to a note in a folder, include the folder path before the note name." "Folder paths start at the vault root and use forward slashes (`/`), even on Windows."
- `[[#Preview a linked file]]` heading in the same note; `[[About Obsidian#Links are first-class citizens]]` heading in another note; `[[Help and support#Questions and advice#Report bugs and request features]]` for sub-headings.
- `[[2023-01-01#^37066d]]` block link. "Block identifiers can only consist of Latin letters, numbers, and dashes." Write a paragraph id at line end (`text ^id`); for lists, quotes, callouts and tables put ` ^id` on its own line with blank lines around it. Human-readable ids are allowed (`^my-list-id`).
- `[[Example|Custom name]]` display text.
- Embeds use the same forms with `!` prefix: `![[Note]]`, `![[Note#Heading]]`, `![[Note#^id]]`. Source: https://obsidian.md/help/embeds

**Alias resolution.** An alias is never a link target. Obsidian writes `[[Real name|Alias]]`. Source: https://obsidian.md/help/aliases. A parser that meets `[[X]]` should first try `X` as a file path, then as a full path, and only then as an alias if the index wants alias lookup as a fallback (this fallback is our own design choice; Obsidian itself does not resolve `[[Alias]]`).

**Subfolders and the link format setting.** Settings > Files and links:
- "Use [[Wikilinks]]": "Auto-generate Wikilinks for `[[links]]` and `![[images]]` instead of Markdown links and images."
- "New link format": "Shortest path when possible" = "Uses the shortest unique path to the linked file."; "Relative path to file" = "Uses a path relative to the current file."; "Absolute path in vault" = "Uses the full path from the vault root."
- "Automatically update internal links": "When enabled, Obsidian automatically updates internal links when you rename a file."
Source: https://obsidian.md/help/settings

The setting only controls what Obsidian *writes*. How it *reads* an ambiguous short name (two `Tomate.md` in different folders) is not documented on the help site. The API exposes `MetadataCache.getFirstLinkpathDest(linkpath, sourcePath): TFile | null` ("Get the best match for a linkpath"), and `getLinkpath(linktext)` strips `#heading`/`|display` to get the path part. Sources: https://docs.obsidian.md/Reference/TypeScript+API/MetadataCache/getFirstLinkpathDest, https://docs.obsidian.md/Reference/TypeScript+API/getLinkpath

**Recommendation for the index builder.** Require unique base names across the vault (a lint rule) so `[[note]]` is never ambiguous, and set "New link format" to "Shortest path when possible" (the default behaviour that produces `[[note]]`). Accept `[[folder/note]]` and `[[note.md]]` as equivalent to `[[note]]`. Case sensitivity of link resolution is not documented; treat names as case-insensitive-unique to be safe (see Unverified).

### Q3. File name constraints

Official statement: "Obsidian will respect the filename limitations of the operating system you create the note on." For sync across devices "make sure your filenames are safe for other operating systems" (links to https://stackoverflow.com/q/1976007). Renaming a note updates all links automatically. Source: https://obsidian.md/help/manage-notes

The help site does not publish a list of characters Obsidian itself blocks. From the link syntax alone (Q2) the characters `[`, `]`, `#`, `^`, `|` cannot appear in a linkable name because they delimit link parts. From OS rules, avoid `\ / : * ? " < >` and leading dots. The combined list `[ ] # ^ |` plus `\ / :` (all OS) and `* " ?` (Windows) appears only on the community forum (see Unverified).

**Recommendation.** Node file names: ASCII letters, digits, spaces, `-`, `_`, and German umlauts (`ä ö ü ß`) are acceptable; never use `[ ] # ^ | \ / : * ? " < >` or a leading dot. Keep the canonical name in the file name and put the German printed label in `aliases`.

### Q4. Inline fields `key:: value`

The Obsidian "Basic formatting syntax" page has no section on inline fields and the `::` syntax does not appear on it. Source: https://obsidian.md/help/syntax. The Properties page defines metadata only as frontmatter. Source: https://obsidian.md/help/properties

The `Key:: Value` syntax is defined by the Dataview community plugin: "Dataview supports 'inline' fields using a `Key:: Value` syntax that you can use everywhere in your file." and "All YAML Frontmatter fields will be automatically available as Dataview fields." Source: https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/

**Conclusion.** Inline fields are Dataview-only. Core Obsidian renders `key:: value` as plain text. Do not use them for machine-readable data; use frontmatter.

### Q5. Templates and Daily notes (one node per day)

**Daily notes core plugin.** Creates notes named by a date format, default `YYYY-MM-DD`. Settings: "New file location", "Date format", "Template file location". The date format uses moment.js tokens, and a format with slashes creates folders: `YYYY/MMMM/YYYY-MMM-DD` gives `2023/January/2023-Jan-01`. "When the Daily notes plugin is activated and a date property is present within any note, Obsidian will automatically attempt to generate a link to the daily note for that specific day." Source: https://obsidian.md/help/plugins/daily-notes

**Templates core plugin.** Settings: "Template folder location", "Date format", "Time format". Variables: `{{title}}` ("Title of the active note"), `{{date}}` (default `YYYY-MM-DD`), `{{time}}` (default `HH:mm`), with overrides such as `{{date:YYYY-MM-DD}}`. Warning: "In Live Preview, the Properties in document panel can overwrite template variables that do not have quotation marks." Fix: quote the values, edit templates in Source mode, or set Settings > Editor > Properties in document to Source. Source: https://obsidian.md/help/plugins/templates

**Recommendation for Day nodes.** Name Day files `YYYY-MM-DD.md`, keep the Daily notes date format at the default, set "New file location" to the Day folder, and point "Template file location" to a Day template. Put `date: "{{date:YYYY-MM-DD}}"` in the template (quoted). Then a `date` property in any Meal or Pantry node links to that Day node for free.

## Recommended Food node frontmatter

All values use core types only: Text, List, Number, Checkbox, Date, Tags. No nested objects. Serving aliases and sources are plain strings so they stay human-readable and stay one type vault-wide.

```yaml
---
type: food
name: Meatball beef
aliases:
  - Rinderfleischbällchen
  - Fleischbällchen
tags:
  - food
  - protein-source
label_name: Rinderfleischbällchen
brand: Ja! Natürlich
kcal_per_100g: 245
protein_g_per_100g: 17.5
fat_g_per_100g: 18
carbs_g_per_100g: 3.2
servings:
  - "1 meatball = 30 g"
  - "1 portion = 120 g"
number_source: label
source_url: "https://example.com/product/123"
verified: true
updated: 2026-09-10
pantry: "[[Pantry]]"
---
```

Rules that keep this shape parseable and Obsidian-safe:

1. `type` is a Text property with a fixed vocabulary: `food`, `meal`, `day`, `goals`, `pantry`. Obsidian has no reserved `type` property.
2. `aliases` and `tags` are lists, no `#` on tags, no spaces in tags.
3. Numbers are literal numbers (no units, no `=`), so Obsidian shows them as Number. Put the unit in the key name.
4. Each `servings` item is one string in double quotes. The index builder parses `"<n> <unit> = <grams> g"` itself.
5. Links inside properties are quoted strings: `"[[Pantry]]"`. Obsidian indexes them in `frontmatterLinks`.
6. Dates are `YYYY-MM-DD` and unquoted, so Obsidian shows a date picker and links to the Day node.
7. Use the same key name for the same meaning in every node type, because a property name has one type across the vault.
8. Keep body content (headings, notes) below the frontmatter; the index builder reads headings and body wikilinks from there.

## Unverified

- The complete list of characters Obsidian blocks in note names (`[ ] # ^ |` on all systems, `\ / :` on macOS/Linux, `* " \ / : | ?` on Windows, no leading dot) comes from community forum posts, not from the official help site. Forum: https://forum.obsidian.md/t/valid-characters-for-file-names/55307 and https://forum.obsidian.md/t/list-of-all-forbidden-filename-characters/103977. Confirm in the app by trying to rename a note.
- How Obsidian resolves an ambiguous `[[name]]` when two files share a base name in different folders. The API only says "best match". Unverified; the vault should avoid duplicate base names.
- Case sensitivity of link resolution and of property names. Not documented on the help site.
- Exact UI behaviour for a nested YAML object or an invalid YAML block (what the Properties panel shows). The help page only says nested properties are unsupported and recommends source mode.
- Whether the Properties panel accepts a Text value that is a bare number without converting it (relevant for `number_source` values that could be numeric). Not documented.
- The Publish properties page (`obsidian.md/help/publish/properties`) returned 404; the property names are taken from the Properties page.

## Sources

Obsidian Help (primary):
- Properties: https://obsidian.md/help/properties
- Aliases: https://obsidian.md/help/aliases
- Tags: https://obsidian.md/help/tags
- Internal links: https://obsidian.md/help/links
- Embeds: https://obsidian.md/help/embeds
- Settings (Files and links): https://obsidian.md/help/settings
- Manage notes (file name limits): https://obsidian.md/help/manage-notes
- Basic formatting syntax: https://obsidian.md/help/syntax
- File formats: https://obsidian.md/help/file-formats
- Daily notes plugin: https://obsidian.md/help/plugins/daily-notes
- Templates plugin: https://obsidian.md/help/plugins/templates

Obsidian Developer Docs (primary):
- CachedMetadata: https://docs.obsidian.md/Reference/TypeScript+API/CachedMetadata
- FrontmatterLinkCache: https://docs.obsidian.md/Reference/TypeScript+API/FrontmatterLinkCache
- LinkCache: https://docs.obsidian.md/Reference/TypeScript+API/LinkCache
- MetadataCache.getFirstLinkpathDest: https://docs.obsidian.md/Reference/TypeScript+API/MetadataCache/getFirstLinkpathDest
- getLinkpath: https://docs.obsidian.md/Reference/TypeScript+API/getLinkpath
- FileManager.processFrontMatter: https://docs.obsidian.md/Reference/TypeScript+API/FileManager/processFrontMatter
- parseFrontMatterAliases: https://docs.obsidian.md/Reference/TypeScript+API/parseFrontMatterAliases

Specifications and plugin docs:
- YAML 1.2.2: https://yaml.org/spec/1.2.2/
- Dataview inline fields (plugin, not core): https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/

Secondary (forum, used only in the Unverified list):
- https://forum.obsidian.md/t/valid-characters-for-file-names/55307
- https://forum.obsidian.md/t/list-of-all-forbidden-filename-characters/103977
