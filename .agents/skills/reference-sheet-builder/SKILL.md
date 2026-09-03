---
name: reference-sheet-builder
description: Designs and compiles standardized character, expression, outfit, prop, and background reference sheets for GPT Image 2. Use when establishing visual canon, creating a new design sheet, or maintaining a recurring character through reference-image edits.
---

# Reference Sheet Builder

Build a visual asset JSON conforming to `schemas/v1/visual-asset.schema.json`, then compile it into a render task.

## Character workflow

1. Read the character's `identity_lock` from the story bible.
2. For the first canonical sheet, specify a clean neutral layout with front, side, and back full-body views plus expression, clothing/equipment details, and palette swatches.
3. Keep scale and costume consistent across all views. Use a plain unobtrusive background and avoid decorative composition.
4. Generate labels later as deterministic overlay unless the user explicitly wants embedded text.
5. Once a sheet is approved, mark it as the first `character_identity` reference in every derivative asset.
6. Use `edit` for expression/outfit/action variants. State the requested change separately from `must_preserve` invariants.

## Background workflow

1. Define the navigable space before mood: plan/elevation or wide establishing view, entrances, fixed landmarks, horizon, scale anchors, and lighting variants.
2. Preserve layout and architectural anchors across later crops.
3. Add the approved environment sheet as a `background_space` reference in shot briefs.

## Compile

```powershell
python tools/compile_visual_tasks.py <visual-asset.json> --project-root <project-root>
python tools/run_image_tasks.py <render-task.json> --project-root <project-root>
```

The second command is a dry run unless `--execute` is explicitly supplied after user approval.
