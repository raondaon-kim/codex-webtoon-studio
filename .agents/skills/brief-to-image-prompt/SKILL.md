---
name: brief-to-image-prompt
description: Deterministically transforms validated director briefs or visual asset plans into provider-neutral image prompts and gpt-image-2-skill render tasks. Use when compiling prompts, preparing image jobs, selecting generate versus edit, or reviewing exactly what an image model will receive.
---

# Brief to Image Prompt

Keep this stage mechanical. Do not invent new plot, costume, layout, or character identity facts while compiling.

## Procedure

1. Validate the source brief or visual asset.
2. Resolve reference paths relative to the project root.
3. Preserve declared reference order and annotate each image's index and role in the prompt.
4. Choose `edit` whenever at least one approved identity/space reference exists; otherwise choose `generate`.
5. Build the prompt in this order:
   - artifact and canvas purpose
   - composition/camera
   - subject placement using approximate percentages from bboxes
   - background space/crop/depth
   - visual treatment and lighting
   - reference roles and invariants
   - deterministic lettering exclusions and negative constraints
   - when `bridge` is declared, its exact 2- or 3-panel vertical composite instruction and ordered micro-beats
6. Save `source_hash` from the canonical source JSON.
7. Compile and verify idempotence:

```powershell
python tools/compile_render_tasks.py <brief-file-or-directory> --project-root <project-root> --check
```

A bridge composite remains one render task and one output image. Never expand its mini-panels into separate image calls during compilation.

## Provider boundary

- Render tasks contain no credentials.
- For Codex, omit OpenAI-only flags such as mask and input fidelity.
- Do not silently switch providers.
- Do not execute paid work; compilation is a separate action from execution.
