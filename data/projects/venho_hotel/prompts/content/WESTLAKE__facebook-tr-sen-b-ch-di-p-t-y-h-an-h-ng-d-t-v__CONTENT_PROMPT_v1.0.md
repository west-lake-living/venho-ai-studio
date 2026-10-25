# PROMPT FILE

## META

- contract_version: 1.0
- module: prompt_studio
- project: venho_hotel
- prompt_type: content
- prompt_id: westlake__content__facebook-tr-sen-b-ch-di-p-t-y-h-an-h-ng-d-t-v
- prompt_version: 1.0
- generated_at: 2026-10-25T13:29:12.304968+00:00
- target_language: vi
- template: content_prompt.yaml (v1.0)
- optimizer: used=False

## TASK BRIEF

Create a facebook_post draft about 'Trà sen Bách Diệp Tây Hồ đan hương dệt vị' for Vietnamese leisure guests. Content pillar: Trend Radar. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

## SOURCE KNOWLEDGE

- VENHO_HOTEL_WESTLAKE_DNA.json — dna_version=1.2, dna_contract_version=1.1, hash=sha256:61f198440f5480c3ab7b63c38c97553d7cf072838b82dcdd5e4d802521e67a38

## REQUIRED DNA

- water_reflection_quality: minimal
- tree_density: moderate
- water_color: muted jade-teal #4E8FA0 — calm, reflective, not tropical blue
- water_visibility_range: far
- sky_condition: partly_cloudy
- distant_cityscape: yes
- lamp_post_presence: no
- water_surface_texture: calm
- light_quality: soft
- haze_level: none

## ALLOWED VARIATIONS

- human_activity: none / sparse
- railing_presence: false / partial / true
- general_scene_character: urban lakeside with buildings and trees / urban lakeside with city lights reflecting on calm water / urban lakeside with cyclist and trees / urban lakeside with distant buildings / urban lakeside with distant city skyline / urban lakeside with moderate vegetation and distant buildings / urban lakeside with moderate vegetation and distant cityscape / urban skyline with illuminated buildings reflecting on calm water
- path_presence: false / true
- vegetation_presence: false / true
- time_of_day: afternoon / midday / morning / night

## ALLOWED IMPERFECTIONS

- slight Hanoi haze or atmospheric softness acceptable — authentic weather (source: curated)
- natural water texture variation (ripples, reflections) acceptable (source: curated)
- modest street-level elements (motorbikes, vendors) acceptable — real life (source: curated)
- overcast or grey sky acceptable — not all shots need golden hour (source: curated)
- slight color variation in water between morning and afternoon acceptable (source: curated)
- slight cloud cover (source: observed)
- natural water color variation (source: observed)
- some leafless trees (source: observed)
- slight haze in the distance (source: observed)
- clouds partially obscure sky (source: observed)
- slightly uneven pavement (source: observed)
- slight haze over cityscape (source: observed)

## FORBIDDEN / RESTRICTIONS

- no tourist postcard aesthetic — must feel like daily local life, not staged (source: curated)
- no generic Asian city lake — must be distinctly Ho Tay / Hanoi (source: curated)
- no artificial or manicured park look — natural, unhurried (source: curated)
- no resort waterfront design — this is public lakeside street, not hotel grounds (source: curated)
- no dramatic staged lighting — soft Hanoi haze and natural glow only (source: curated)
- no saturated or oversaturated water color — must be muted jade-teal, not tropical blue (source: curated)
- no modern glass high-rise dominating the frame — a distant, hazy low/mid-rise skyline across the far shore is real West Lake and is fine (source: curated)
- no tourist postcard aesthetic (source: observed)
- no generic Asian city lake (source: observed)
- no artificial or manicured park look (source: observed)
- no resort waterfront design (source: observed)
- no dramatic/staged lighting (source: observed)
- no manicured resort waterfront (source: observed)
- no tourist postcard aesthetic — must feel like daily local life, not staged
- no generic Asian city lake — must be distinctly Ho Tay / Hanoi
- no artificial or manicured park look — natural, unhurried
- no resort waterfront design — this is public lakeside street, not hotel grounds
- no dramatic staged lighting — soft Hanoi haze and natural glow only
- no saturated or oversaturated water color — must be muted jade-teal, not tropical blue
- no modern glass high-rise dominating the frame — a distant, hazy low/mid-rise skyline across the far shore is real West Lake and is fine
- no tourist postcard aesthetic
- no generic Asian city lake
- no artificial or manicured park look
- no resort waterfront design
- no dramatic/staged lighting
- no manicured resort waterfront
- Do not claim '5 star' or 'best in Hanoi' — Ven Ho Hotel is boutique mid-range, not luxury.
- Do not use the phrase 'sang chảnh nhất' or overclaim luxury positioning.
- Do not fabricate guest reviews, ratings, or awards not present in Knowledge.
- Do not describe West Lake as a generic tourist postcard — keep it authentic, local, unhurried.

## FINAL PROMPT

Create a facebook_post draft about 'Trà sen Bách Diệp Tây Hồ đan hương dệt vị' for Vietnamese leisure guests. Content pillar: Trend Radar. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

Write the content in Vietnamese.

Audience: Travelers considering a stay near West Lake (Ho Tay), Hanoi — leisure and business, VN + international.
Tone: Warm, authentic, unhurried. Show real daily life beside West Lake, not a sales pitch.

Brand DNA:
- The West Lake Living — gold #C9A84C accent, deep navy #1B2D4F, warm white #F7F4EF background.
- Tagline: 'Where West Lake Meets Elegance'.
- Ven Ho Hotel is the gateway/base camp of the universe — boutique mid-range, not luxury resort.

Required facts (ground your writing in these, do not contradict them, but never copy hex codes or raw English descriptors literally — paraphrase in the target language):
- water_reflection_quality: minimal
- tree_density: moderate
- water_color: muted jade-teal #4E8FA0 — calm, reflective, not tropical blue
- water_visibility_range: far
- sky_condition: partly_cloudy
- distant_cityscape: yes
- lamp_post_presence: no
- water_surface_texture: calm
- light_quality: soft
- haze_level: none

Flexible details (any one of the listed options is acceptable):
- human_activity: none / sparse
- railing_presence: false / partial / true
- general_scene_character: urban lakeside with buildings and trees / urban lakeside with city lights reflecting on calm water / urban lakeside with cyclist and trees / urban lakeside with distant buildings / urban lakeside with distant city skyline / urban lakeside with moderate vegetation and distant buildings / urban lakeside with moderate vegetation and distant cityscape / urban skyline with illuminated buildings reflecting on calm water
- path_presence: false / true
- vegetation_presence: false / true
- time_of_day: afternoon / midday / morning / night

Call-to-action: End with one soft call-to-action inviting the reader to check availability or message the page — never pushy, never a hard sell.

## VALIDATION

- structural: pending
- faithfulness: pending

## NOTES

(none)
