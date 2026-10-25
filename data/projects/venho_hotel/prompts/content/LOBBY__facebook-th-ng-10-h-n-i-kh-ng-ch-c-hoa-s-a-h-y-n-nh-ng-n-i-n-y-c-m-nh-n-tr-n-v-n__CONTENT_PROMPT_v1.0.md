# PROMPT FILE

## META

- contract_version: 1.0
- module: prompt_studio
- project: venho_hotel
- prompt_type: content
- prompt_id: lobby__content__facebook-th-ng-10-h-n-i-kh-ng-ch-c-hoa-s-a-h-y-n-nh-ng-n-i-n-y-c-m-nh-n-tr-n-v-n
- prompt_version: 1.0
- generated_at: 2026-10-25T13:12:36.464981+00:00
- target_language: vi
- template: content_prompt.yaml (v1.0)
- optimizer: used=False

## TASK BRIEF

Create a facebook_post draft about 'Tháng 10, Hà Nội không chỉ có hoa sữa: Hãy đến những nơi này để cảm nhận trọn vẹn hương sắc mùa thu' for Vietnamese leisure guests. Content pillar: Trend Radar. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

## SOURCE KNOWLEDGE

- VENHO_HOTEL_LOBBY_DNA.json — dna_version=1.1, dna_contract_version=1.1, hash=sha256:e01fc1fa26c2318ce93d3a670067bac2ccbf9dc329a141ea906e80fb108c673f

## REQUIRED DNA

- ceiling_treatment: flat_white
- cleanliness: clean
- wall_artwork: present
- ambient_lighting: neutral
- hotel_signage: logo_visible
- floor_material: tile
- floor_color: brown with circular patterns
- entrance_door: glass_door
- hotel_tier_impression: mid_range
- furniture_wood_tone: dark_reddish_brown
- staircase_visible: False

## ALLOWED VARIATIONS

- wall_treatment: painted_smooth / tile
- pendant_or_chandelier: ceiling_recessed / chandelier / none / pendant_lights
- style_category: generic_hotel / traditional_asian
- waiting_seating: chairs / none
- key_cabinet: present
- natural_light: high / low / moderate / none
- scale: compact / medium
- reception_desk: present_wood
- plants: none / present_multiple / present_single

## ALLOWED IMPERFECTIONS

- slight wear on reception desk surface acceptable (source: curated)
- minor asymmetry in decorative arrangement acceptable (source: curated)
- natural lighting variation across time of day acceptable (source: curated)
- small personal items on reception counter acceptable — authentic, not sterile (source: curated)

## FORBIDDEN / RESTRICTIONS

- no marble floor — actual flooring is tile or stone, not polished marble (source: curated)
- no luxury hotel chandeliers — lighting is warm and functional, not grand (source: curated)
- no resort-scale lobby — this is a compact boutique reception, not a 5-star atrium (source: curated)
- no modern minimalist glass-and-steel design (source: curated)
- no generic international hotel style (source: curated)
- no over-staged decorative props — keep it authentic Vietnamese boutique (source: curated)
- no marble floor (source: observed)
- no luxury hotel chandeliers (source: observed)
- no resort-scale lobby (source: observed)
- no Dubai-style luxury interior (source: observed)
- no marble grand staircase (source: observed)
- no marble floor — actual flooring is tile or stone, not polished marble
- no luxury hotel chandeliers — lighting is warm and functional, not grand
- no resort-scale lobby — this is a compact boutique reception, not a 5-star atrium
- no modern minimalist glass-and-steel design
- no generic international hotel style
- no over-staged decorative props — keep it authentic Vietnamese boutique
- no marble floor
- no luxury hotel chandeliers
- no resort-scale lobby
- no Dubai-style luxury interior
- no marble grand staircase
- Do not claim '5 star' or 'best in Hanoi' — Ven Ho Hotel is boutique mid-range, not luxury.
- Do not use the phrase 'sang chảnh nhất' or overclaim luxury positioning.
- Do not fabricate guest reviews, ratings, or awards not present in Knowledge.
- Do not describe West Lake as a generic tourist postcard — keep it authentic, local, unhurried.

## FINAL PROMPT

Create a facebook_post draft about 'Tháng 10, Hà Nội không chỉ có hoa sữa: Hãy đến những nơi này để cảm nhận trọn vẹn hương sắc mùa thu' for Vietnamese leisure guests. Content pillar: Trend Radar. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

Write the content in Vietnamese.

Audience: Travelers considering a stay near West Lake (Ho Tay), Hanoi — leisure and business, VN + international.
Tone: Warm, authentic, unhurried. Show real daily life beside West Lake, not a sales pitch.

Brand DNA:
- The West Lake Living — gold #C9A84C accent, deep navy #1B2D4F, warm white #F7F4EF background.
- Tagline: 'Where West Lake Meets Elegance'.
- Ven Ho Hotel is the gateway/base camp of the universe — boutique mid-range, not luxury resort.

Required facts (ground your writing in these, do not contradict them, but never copy hex codes or raw English descriptors literally — paraphrase in the target language):
- ceiling_treatment: flat_white
- cleanliness: clean
- wall_artwork: present
- ambient_lighting: neutral
- hotel_signage: logo_visible
- floor_material: tile
- floor_color: brown with circular patterns
- entrance_door: glass_door
- hotel_tier_impression: mid_range
- furniture_wood_tone: dark_reddish_brown
- staircase_visible: False

Flexible details (any one of the listed options is acceptable):
- wall_treatment: painted_smooth / tile
- pendant_or_chandelier: ceiling_recessed / chandelier / none / pendant_lights
- style_category: generic_hotel / traditional_asian
- waiting_seating: chairs / none
- key_cabinet: present
- natural_light: high / low / moderate / none
- scale: compact / medium
- reception_desk: present_wood
- plants: none / present_multiple / present_single

Call-to-action: End with one soft call-to-action inviting the reader to check availability or message the page — never pushy, never a hard sell.

## VALIDATION

- structural: pending
- faithfulness: pending

## NOTES

(none)
