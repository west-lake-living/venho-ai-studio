# Video Studio

Module 06 turns Knowledge-backed production goals into pre-render video production packages.

Boundaries:

- Module 02 builds DNA-faithful scene prompts.
- Module 05 supplies caption, hook, voiceover, and CTA text.
- Video Studio owns temporal structure: concept, storyboard, shot list, continuity, engine formatting, and package output.
- Rendering, publishing, post-production, and post-render video validation stay outside this module.
- Spatial and brand forbidden rules stay in the prompt/DNA layer; video config only contains video-layer rules such as camera, motion, platform, character, and motion negatives.

Current MVP:

- Builds social reel, lifestyle, character, website hero, and explainer package variants through shared orchestration.
- Calls Module 02 for every scene prompt.
- Calls Module 05 for caption/hook/CTA text.
- Checks total scene duration and continuity keys before writing output.
- Writes `.md` and `.json` packages under `data/projects/<project>/video/packages/`.
- Updates `data/projects/<project>/video/video_manifest.json`.
- Validator bridge uses Module 03 prompt validation when available and degrades to `not_available` for future video-package validation.

Example:

```bash
venho-video generate --topic "lake view room morning" --duration 15 --type social_reel --subjects lake_view_room,westlake
```
