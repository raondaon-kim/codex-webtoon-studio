---
name: territory-foundation
description: Establishes the geographic, ecological, economic, infrastructural, political, and chronic constraints of a webtoon territory before choosing individual disasters or episode crises. Use when designing a new territory, its natural environment, chronic problems, or the structural causes of recurring disasters.
---

# Territory Foundation

Create the setting that produces stories; do not choose a convenient crisis first.

## Output

- Create or revise `territory/<territory-id>-profile.json` against `schemas/v1/territory-profile.schema.json`.
- Keep the story bible's location summary aligned with the profile, without duplicating every field.
- Validate it with `python tools/validate_artifacts.py <project-root>/territory`.

## Design order

1. Fix regional position, landforms, watershed, settlement pattern, and visual anchors.
2. Define the seasonal climate cycle and resources, including why each apparent asset is not already solving the territory's problems.
3. Establish population, roads, storage, crossings, waterworks, and other infrastructure that constrains action.
4. Write chronic problems as systems: symptom, root causes, downstream effects, the opportunity created by managing them, and who must decide or act.
5. List disaster exposures only as conditional chains. Each must set `scenario_not_scheduled` to `true`; selecting a specific season's disaster belongs to later story or episode work.

## Continuity rules

- Separate persistent exposure (terrain, climate, ownership, neglected works) from an incident that happens in a particular episode.
- A repair consumes labor, money, political trust, or another scarce resource; it cannot erase a geographic constraint without consequences.
- Put command, rescue, training, and battlefield choices with the field leader; put supply, accounting, incentives, and long-horizon prioritization with the administrator. Shared decisions should create sibling drama rather than merge their roles.
- Give every chronic problem a potential gain. A marsh can provide reeds, fish, transport, or defensible terrain even while it causes hardship.
- Preserve visual anchors so later reference sheets and director briefs can show the same terrain from different distances and crops.
