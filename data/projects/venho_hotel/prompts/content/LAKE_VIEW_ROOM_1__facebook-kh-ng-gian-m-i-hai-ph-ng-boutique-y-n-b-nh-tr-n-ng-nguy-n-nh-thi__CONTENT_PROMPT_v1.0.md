# PROMPT FILE

## META

- contract_version: 1.0
- module: prompt_studio
- project: venho_hotel
- prompt_type: content
- prompt_id: lake_view_room_1__content__facebook-kh-ng-gian-m-i-hai-ph-ng-boutique-y-n-b-nh-tr-n-ng-nguy-n-nh-thi
- prompt_version: 1.0
- generated_at: 2026-10-25T13:09:41.111480+00:00
- target_language: vi
- template: content_prompt.yaml (v1.0)
- optimizer: used=False

## TASK BRIEF

Create a facebook_post draft about 'Không gian mười hai phòng boutique yên bình trên đường Nguyễn Đình Thi' for Vietnamese leisure guests. Content pillar: Khong gian boutique Ven Ho Hotel. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

## SOURCE KNOWLEDGE

- VENHO_HOTEL_LAKE_VIEW_ROOM_1_DNA.json — dna_version=1.2, dna_contract_version=1.1, hash=sha256:7c635dcdc575c74c8263cc1ade2f2b051b2359afc6ca2fc7b55067e64a2cc2f0

## REQUIRED DNA

- room_shape: rectangular
- window_layout: 2x2 grid window layout
- lighting_condition: natural daylight
- style_category: boutique Vietnamese heritage hotel
- bedding_color: white
- wall_artwork: none
- hotel_tier: boutique mid-range
- window_frame: matte black aluminum window frame, thin profile, grid pattern
- wall_color: light gray

## ALLOWED VARIATIONS

- bed_size: double
- wood_tone: dark_reddish_brown / medium_brown
- lake_view_visible: false / partial / true
- curtain_color: dark / dark_blue / dark_gray / gray
- ceiling: decorative_molding / flat_white
- floor: hardwood / laminate / tile
- chairs: none / one_chair / two_wooden
- desk: present_with_mirror / present_without_mirror
- bed_headboard: wooden

## ALLOWED IMPERFECTIONS

- minor scuff marks on skirting boards acceptable (source: curated)
- slight curtain wrinkles acceptable (source: curated)
- small wear marks on wooden furniture edges acceptable (source: curated)
- natural aging of wooden headboard acceptable (source: curated)
- slight unevenness in curtain hang acceptable (source: curated)
- slightly uneven curtain (source: observed)
- slightly uneven floor (source: observed)
- slightly uneven bedding (source: observed)
- slightly wrinkled bedding (source: observed)
- slightly uneven paint on window frame (source: observed)
- slightly uneven wall paint (source: observed)

## FORBIDDEN / RESTRICTIONS

- no floor-to-ceiling glass wall — actual window is grid-pane black aluminum (source: curated)
- no Dubai-style luxury interior (source: curated)
- no generic resort look (source: curated)
- no marble flooring (source: curated)
- no cream and beige luxury palette (source: curated)
- no Korean hotel style (source: curated)
- no generic international hotel design (source: curated)
- no rooftop or outdoor scene — this is an interior room (source: curated)
- no floor-to-ceiling glass wall (source: observed)
- no luxury apartment style (source: observed)
- no marble interior (source: observed)
- no resort aesthetic (source: observed)
- no generic international hotel (source: observed)
- no infinity pool (source: observed)
- no visible wardrobe (source: observed)
- no visible desk (source: observed)
- no chairs present (source: observed)
- no visible chairs (source: observed)
- no visible ceiling details (source: observed)
- no visible floor details (source: observed)
- no wall artwork (source: observed)
- no ceiling visible (source: observed)
- no floor visible (source: observed)
- no wall color visible (source: observed)
- no room shape visible (source: observed)
- no bed size visible (source: observed)
- no bed headboard visible (source: observed)
- no desk visible (source: observed)
- no chairs visible (source: observed)
- no wardrobe visible (source: observed)
- no wood tone visible (source: observed)
- no wall artwork visible (source: observed)
- no window view (source: observed)
- no visible bed (source: observed)
- no visible curtains (source: observed)
- no interior room features (source: observed)
- no visible wood tone (source: observed)
- no visible curtain (source: observed)
- no visible style category (source: observed)
- no visible hotel tier (source: observed)
- no visible wall artwork (source: observed)
- no floor-to-ceiling glass wall — actual window is grid-pane black aluminum
- no Dubai-style luxury interior
- no generic resort look
- no marble flooring
- no cream and beige luxury palette
- no Korean hotel style
- no generic international hotel design
- no rooftop or outdoor scene — this is an interior room
- no floor-to-ceiling glass wall
- no luxury apartment style
- no marble interior
- no resort aesthetic
- no generic international hotel
- no infinity pool
- no visible wardrobe
- no visible desk
- no chairs present
- no visible chairs
- no visible ceiling details
- no visible floor details
- no wall artwork
- no ceiling visible
- no floor visible
- no wall color visible
- no room shape visible
- no bed size visible
- no bed headboard visible
- no desk visible
- no chairs visible
- no wardrobe visible
- no wood tone visible
- no wall artwork visible
- no window view
- no visible bed
- no visible curtains
- no interior room features
- no visible wood tone
- no visible curtain
- no visible style category
- no visible hotel tier
- no visible wall artwork
- Do not claim '5 star' or 'best in Hanoi' — Ven Ho Hotel is boutique mid-range, not luxury.
- Do not use the phrase 'sang chảnh nhất' or overclaim luxury positioning.
- Do not fabricate guest reviews, ratings, or awards not present in Knowledge.
- Do not describe West Lake as a generic tourist postcard — keep it authentic, local, unhurried.

## FINAL PROMPT

Create a facebook_post draft about 'Không gian mười hai phòng boutique yên bình trên đường Nguyễn Đình Thi' for Vietnamese leisure guests. Content pillar: Khong gian boutique Ven Ho Hotel. Tone: warm, clear, trustworthy. Length: medium. CTA type: booking_soft.

Write the content in Vietnamese.

Audience: Travelers considering a stay near West Lake (Ho Tay), Hanoi — leisure and business, VN + international.
Tone: Warm, authentic, unhurried. Show real daily life beside West Lake, not a sales pitch.

Brand DNA:
- The West Lake Living — gold #C9A84C accent, deep navy #1B2D4F, warm white #F7F4EF background.
- Tagline: 'Where West Lake Meets Elegance'.
- Ven Ho Hotel is the gateway/base camp of the universe — boutique mid-range, not luxury resort.

Required facts (ground your writing in these, do not contradict them, but never copy hex codes or raw English descriptors literally — paraphrase in the target language):
- room_shape: rectangular
- window_layout: 2x2 grid window layout
- lighting_condition: natural daylight
- style_category: boutique Vietnamese heritage hotel
- bedding_color: white
- wall_artwork: none
- hotel_tier: boutique mid-range
- window_frame: matte black aluminum window frame, thin profile, grid pattern
- wall_color: light gray

Flexible details (any one of the listed options is acceptable):
- bed_size: double
- wood_tone: dark_reddish_brown / medium_brown
- lake_view_visible: false / partial / true
- curtain_color: dark / dark_blue / dark_gray / gray
- ceiling: decorative_molding / flat_white
- floor: hardwood / laminate / tile
- chairs: none / one_chair / two_wooden
- desk: present_with_mirror / present_without_mirror
- bed_headboard: wooden

Call-to-action: End with one soft call-to-action inviting the reader to check availability or message the page — never pushy, never a hard sell.

## VALIDATION

- structural: pending
- faithfulness: pending

## NOTES

(none)
