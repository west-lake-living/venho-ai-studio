# PROMPT FILE

## META

- contract_version: 1.0
- module: prompt_studio
- project: venho_hotel
- prompt_type: content
- prompt_id: outside__content__facebook-skyon9-rooftop-west-lake-t-y-h-h-n-i
- prompt_version: 1.0
- generated_at: 2026-10-25T13:06:04.534253+00:00
- target_language: vi
- template: content_prompt.yaml (v1.0)
- optimizer: used=False

## TASK BRIEF

Create a facebook_post draft about 'Skyon9 Rooftop West Lake (Tây Hồ, Hà Nội)' for Vietnamese leisure guests. Content pillar: Diem den & su kien quanh Ho Tay. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

## SOURCE KNOWLEDGE

- VENHO_HOTEL_OUTSIDE_DNA.json — dna_version=1.2, dna_contract_version=1.1, hash=sha256:aaad1f90ca3a80fbefe9dc168823190c89ef923952e96bd2d902e73f0c5ec577

## REQUIRED DNA

- cityscape_visible: mixed cityscape visible
- sky_condition: clear blue sky
- street_trees_visible: mature street trees visible
- lighting_condition: natural daylight
- space_condition: well maintained space
- outdoor_furniture: no outdoor furniture

## ALLOWED VARIATIONS

- lake_view_visible: full_panoramic / none / partial
- lake_water_color: blue_gray / jade_teal
- floor_level: ground_floor / upper_floor
- space_type: balcony / entrance_area / rooftop_terrace / street_level_exterior
- flooring_material: concrete / tile
- time_of_day: afternoon / midday
- plants_present: none / yes_landscaped / yes_potted
- railing_type: black_iron_scroll / concrete_parapet / metal_bar / none

## ALLOWED IMPERFECTIONS

- Hanoi haze over lake view acceptable and authentic (source: curated)
- weathered tiles or concrete surface acceptable (source: curated)
- visible neighboring rooftops acceptable (source: curated)
- natural sky variation (clouds, smog) acceptable (source: curated)
- modest outdoor furniture showing wear acceptable (source: curated)
- Some dirt or wear on the building facade (source: observed)
- motorbikes parked on sidewalk (source: observed)
- none (source: observed)
- Some trees appear to have dry branches. (source: observed)
- slight cloud cover (source: observed)
- Some buildings show signs of wear. (source: observed)
- Some dirt on the street (source: observed)
- slightly uneven pavement (source: observed)
- slightly worn facade (source: observed)
- slight wear on pavement (source: observed)
- Some shadows on the pavement (source: observed)

## FORBIDDEN / RESTRICTIONS

- no infinity pool or resort-style pool deck — hotel has no pool (source: curated)
- no rooftop bar with full commercial bar setup (source: curated)
- no luxury resort terrace furniture (cabanas, daybeds) (source: curated)
- no modern glass high-rise dominating the frame — a distant, hazy skyline across the water is real West Lake and is fine (source: curated)
- no generic rooftop lounge aesthetic — this is a simple urban terrace (source: curated)
- no manicured hotel garden — space is compact and urban (source: curated)
- no infinity pool or resort-style pool deck (source: observed)
- no rooftop bar with full bar setup (source: observed)
- no luxury resort terrace furniture (source: observed)
- no city high-rise skyline in background (source: observed)
- No visible outdoor furniture (source: observed)
- No visible plants on the balcony (source: observed)
- No visible flooring material (source: observed)
- No specific outdoor furniture (source: observed)
- No visible railing (source: observed)
- No visible outdoor furniture or specific flooring material (source: observed)
- No people visible (source: observed)
- No vehicles other than motorbike (source: observed)
- No visible lake or cityscape (source: observed)
- No outdoor furniture (source: observed)
- no infinity pool or resort-style pool deck — hotel has no pool
- no rooftop bar with full commercial bar setup
- no luxury resort terrace furniture (cabanas, daybeds)
- no modern glass high-rise dominating the frame — a distant, hazy skyline across the water is real West Lake and is fine
- no generic rooftop lounge aesthetic — this is a simple urban terrace
- no manicured hotel garden — space is compact and urban
- no infinity pool or resort-style pool deck
- no rooftop bar with full bar setup
- no luxury resort terrace furniture
- no city high-rise skyline in background
- No visible outdoor furniture
- No visible plants on the balcony
- No visible flooring material
- No specific outdoor furniture
- No visible railing
- No visible outdoor furniture or specific flooring material
- No people visible
- No vehicles other than motorbike
- No visible lake or cityscape
- No outdoor furniture
- Do not claim '5 star' or 'best in Hanoi' — Ven Ho Hotel is boutique mid-range, not luxury.
- Do not use the phrase 'sang chảnh nhất' or overclaim luxury positioning.
- Do not fabricate guest reviews, ratings, or awards not present in Knowledge.
- Do not describe West Lake as a generic tourist postcard — keep it authentic, local, unhurried.

## FINAL PROMPT

Create a facebook_post draft about 'Skyon9 Rooftop West Lake (Tây Hồ, Hà Nội)' for Vietnamese leisure guests. Content pillar: Diem den & su kien quanh Ho Tay. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

Write the content in Vietnamese.

Audience: Travelers considering a stay near West Lake (Ho Tay), Hanoi — leisure and business, VN + international.
Tone: Warm, authentic, unhurried. Show real daily life beside West Lake, not a sales pitch.

Brand DNA:
- The West Lake Living — gold #C9A84C accent, deep navy #1B2D4F, warm white #F7F4EF background.
- Tagline: 'Where West Lake Meets Elegance'.
- Ven Ho Hotel is the gateway/base camp of the universe — boutique mid-range, not luxury resort.

Required facts (ground your writing in these, do not contradict them, but never copy hex codes or raw English descriptors literally — paraphrase in the target language):
- cityscape_visible: mixed cityscape visible
- sky_condition: clear blue sky
- street_trees_visible: mature street trees visible
- lighting_condition: natural daylight
- space_condition: well maintained space
- outdoor_furniture: no outdoor furniture

Flexible details (any one of the listed options is acceptable):
- lake_view_visible: full_panoramic / none / partial
- lake_water_color: blue_gray / jade_teal
- floor_level: ground_floor / upper_floor
- space_type: balcony / entrance_area / rooftop_terrace / street_level_exterior
- flooring_material: concrete / tile
- time_of_day: afternoon / midday
- plants_present: none / yes_landscaped / yes_potted
- railing_type: black_iron_scroll / concrete_parapet / metal_bar / none

Call-to-action: End with one soft call-to-action inviting the reader to check availability or message the page — never pushy, never a hard sell.

## VALIDATION

- structural: pending
- faithfulness: pending

## NOTES

(none)
