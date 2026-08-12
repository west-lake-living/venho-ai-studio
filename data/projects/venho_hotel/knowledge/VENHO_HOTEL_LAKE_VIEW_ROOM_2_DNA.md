# PROJECT SUBJECT DNA

## META

- **project**: venho_hotel
- **subject**: lake_view_room_2
- **schema_id**: venho_hotel.lake_view_room_2
- **schema_version**: 1.0
- **dna_version**: 1.1
- **generated_at**: 2026-08-12T14:59:50.201179
- **provider**: claude
- **model**: claude-sonnet-4-6
- **contract_version**: 1.1
- **total_source_images**: 6


## INVARIANT

*Features that are consistent and stable across all/most images.*

- **lighting_condition**: natural daylight  _(evidence: 6, coverage: 100%, consistency: 100%)_
- **style_category**: boutique Vietnamese heritage hotel `[curated]`  _(evidence: 5, coverage: 83%, consistency: 100%)_
- **room_shape**: rectangular room  _(evidence: 5, coverage: 83%, consistency: 100%)_
- **ceiling**: flat white ceiling  _(evidence: 5, coverage: 83%, consistency: 80%)_
- **bedding_color**: white bedding  _(evidence: 5, coverage: 83%, consistency: 100%)_
- **window_frame**: matte black aluminum window frame, thin profile, grid pattern `[curated]`  _(evidence: 5, coverage: 83%, consistency: 80%)_
- **hotel_tier**: boutique mid-range `[curated]`  _(evidence: 5, coverage: 83%, consistency: 100%)_
- **bed_headboard**: wooden bed headboard  _(evidence: 5, coverage: 83%, consistency: 100%)_
- **chairs**: two wooden chairs  _(evidence: 4, coverage: 67%, consistency: 100%)_
- **curtain_color**: dark gray curtains  _(evidence: 4, coverage: 67%, consistency: 75%)_
- **window_layout**: 2x2 grid window layout  _(evidence: 4, coverage: 67%, consistency: 75%)_


## VARIABLE

*Features that vary across images — all observed values listed.*

- **wall_artwork**: `none` · `single_artwork` · `three_floral_prints`
- **floor**: `hardwood`
- **bed_size**: `double` · `king` · `queen`
- **lake_view_visible**: `false` · `partial` · `true`
- **wall_color**: `light_gray` · `white`
- **desk**: `present_with_mirror`
- **wood_tone**: `dark_reddish_brown` · `medium_brown`


## ALLOWED IMPERFECTIONS

*Naturally occurring imperfections that are acceptable — and preferable for authenticity.*

- minor scuff marks on skirting boards acceptable `[curated]`
- slight curtain wrinkles acceptable `[curated]`
- small wear marks on wooden furniture edges acceptable `[curated]`
- natural aging of wooden headboard acceptable `[curated]`
- slight unevenness in curtain hang acceptable `[curated]`
- slightly uneven curtain `[observed]`
- slightly wrinkled bedding `[observed]`


## FORBIDDEN

*Things NOT present — prevents AI hallucination. Curated rules are policy; observed rules are hints.*

- no floor-to-ceiling glass wall — actual window is grid-pane black aluminum `[curated]`
- no Dubai-style luxury interior `[curated]`
- no generic resort look `[curated]`
- no marble flooring `[curated]`
- no cream and beige luxury palette `[curated]`
- no Korean hotel style `[curated]`
- no generic international hotel design `[curated]`
- no rooftop or outdoor scene — this is an interior room `[curated]`
- no floor-to-ceiling glass wall `[observed]`
- no luxury apartment style `[observed]`
- no marble interior `[observed]`
- no resort aesthetic `[observed]`
- no generic international hotel `[observed]`
- no interior room details `[observed]`
- no visible furniture `[observed]`
- no visible bed `[observed]`
- no visible desk `[observed]`
- no visible chairs `[observed]`
- no visible wardrobe `[observed]`
- no visible curtains `[observed]`
- no visible wall color `[observed]`
- no visible ceiling `[observed]`
- no visible floor `[observed]`
- no infinity pool `[observed]`
- no window view `[observed]`
- no wall artwork `[observed]`


## EVIDENCE

- **total_images**: 6
- **invariant_count**: 11
- **variable_count**: 7
- **source_hashes**: bf0ea5b5, a4c78c6b, 645ca644, 9b30a375, 0fd9333b… (+1 more)


## WEAK FEATURES

*Features seen in too few images to classify. Shoot more images.*

- **wardrobe** (seen in 1 image(s))


## FUTURE CAPTURE NOTES

- Need more images showing 'wardrobe' to confirm invariant status


## CURATOR NOTES

- DEFINING FEATURE: Lake view through black aluminum grid window — must be present
- 16m² floor plan — compact, not spacious — rooms are narrow-long
- Palette reference: Visual DNA v2.7 §12 — warm neutral tones, dark wood accents
- Hotel tier: boutique mid-range on West Lake — NOT luxury resort
- Authenticity principle: trustworthy impression over polished perfection
- Corresponds to room_2 from v2.3 DNA (ceiling: flat_white, lake view)
