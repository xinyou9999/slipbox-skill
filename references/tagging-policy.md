# Tagging policy

## Division of responsibility

The script does deterministic work only: loading the vocabulary, Unicode/case normalization, alias resolution, validation, usage statistics, and literal candidate matching. The Agent decides semantic relevance. No model service is built into the script.

## Before assigning tags

1. Read the full library with `tag-list --json`.
2. Use `tag-list --match "CARD TEXT" --json` for lexical candidates, but do not treat absence or presence as a semantic verdict.
3. Prefer canonical tags already in the library. An alias is accepted on input and stored as its canonical name.
4. Use no more than three tags on one card. Prefer the smallest set that helps future retrieval.
5. Create a tag only when no existing concept fits. Add a clear description and useful aliases with `tag-add` before adding the card.

Unknown tags are rejected. This explicit two-step creation prevents unbounded tag growth.

## Vocabulary maintenance

- A canonical name should describe one durable retrieval concept.
- Aliases cover spelling, language, abbreviation, and old vocabulary; they must not collide across tags.
- Use `tag-merge SOURCE TARGET` for duplicates. The target survives, source names become aliases, and affected cards are rewritten.
- Review `tag-stats` periodically. A high count is not proof a tag is useful; a zero count may indicate a candidate for manual cleanup.
