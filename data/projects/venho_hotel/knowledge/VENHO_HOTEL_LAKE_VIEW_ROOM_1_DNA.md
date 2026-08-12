# PROJECT SUBJECT DNA

## META

- **project**: venho_hotel
- **subject**: lake_view_room_1
- **schema_id**: venho_hotel.lake_view_room_1
- **schema_version**: 1.0
- **dna_version**: 1.2
- **generated_at**: 2026-08-12T14:59:39.207850
- **provider**: claude
- **model**: claude-sonnet-4-6
- **contract_version**: 1.1
- **total_source_images**: 10


## INVARIANT

*Features that are consistent and stable across all/most images.*

- **lighting_condition**: natural daylight  _(evidence: 10, coverage: 100%, consistency: 100%)_
- **style_category**: boutique Vietnamese heritage hotel `[curated]`  _(evidence: 9, coverage: 90%, consistency: 100%)_
- **wall_artwork**: none  _(evidence: 9, coverage: 90%, consistency: 89%)_
- **hotel_tier**: boutique mid-range `[curated]`  _(evidence: 9, coverage: 90%, consistency: 78%)_
- **window_layout**: 2x2 grid window layout  _(evidence: 8, coverage: 80%, consistency: 100%)_
- **bedding_color**: white  _(evidence: 8, coverage: 80%, consistency: 100%)_
- **window_frame**: matte black aluminum window frame, thin profile, grid pattern `[curated]`  _(evidence: 8, coverage: 80%, consistency: 100%)_
- **wall_color**: light gray  _(evidence: 7, coverage: 70%, consistency: 100%)_
- **room_shape**: rectangular  _(evidence: 6, coverage: 60%, consistency: 100%)_


## VARIABLE

*Features that vary across images — all observed values listed.*

- **bed_size**: `double`
- **wood_tone**: `dark_reddish_brown` · `medium_brown`
- **lake_view_visible**: `false` · `partial` · `true`
- **curtain_color**: `dark` · `dark_blue` · `dark_gray` · `gray`
- **ceiling**: `decorative_molding` · `flat_white`
- **floor**: `hardwood` · `laminate` · `tile`
- **chairs**: `none` · `one_chair` · `two_wooden`
- **desk**: `present_with_mirror` · `present_without_mirror`
- **bed_headboard**: `wooden`


## ALLOWED IMPERFECTIONS

*Naturally occurring imperfections that are acceptable — and preferable for authenticity.*

- minor scuff marks on skirting boards acceptable `[curated]`
- slight curtain wrinkles acceptable `[curated]`
- small wear marks on wooden furniture edges acceptable `[curated]`
- natural aging of wooden headboard acceptable `[curated]`
- slight unevenness in curtain hang acceptable `[curated]`
- slightly uneven curtain `[observed]`
- slightly uneven floor `[observed]`
- slightly uneven bedding `[observed]`
- slightly wrinkled bedding `[observed]`
- slightly uneven paint on window frame `[observed]`
- slightly uneven wall paint `[observed]`


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
- no infinity pool `[observed]`
- no visible wardrobe `[observed]`
- no visible desk `[observed]`
- no chairs present `[observed]`
- no visible chairs `[observed]`
- no visible ceiling details `[observed]`
- no visible floor details `[observed]`
- no wall artwork `[observed]`
- no ceiling visible `[observed]`
- no floor visible `[observed]`
- no wall color visible `[observed]`
- no room shape visible `[observed]`
- no bed size visible `[observed]`
- no bed headboard visible `[observed]`
- no desk visible `[observed]`
- no chairs visible `[observed]`
- no wardrobe visible `[observed]`
- no wood tone visible `[observed]`
- no wall artwork visible `[observed]`
- no window view `[observed]`
- no visible bed `[observed]`
- no visible curtains `[observed]`
- no interior room features `[observed]`
- no visible wood tone `[observed]`
- no visible curtain `[observed]`
- no visible style category `[observed]`
- no visible hotel tier `[observed]`
- no visible wall artwork `[observed]`


## EVIDENCE

- **total_images**: 10
- **invariant_count**: 9
- **variable_count**: 9
- **source_hashes**: 7aba2a14, cc998d85, fd31ece4, 0268d54b, 74044521… (+5 more)


## WEAK FEATURES

*Features seen in too few images to classify. Shoot more images.*

*(none)*


## FUTURE CAPTURE NOTES

*(none)*


## CURATOR NOTES

- DEFINING FEATURE: Lake view through black aluminum grid window — must be present
- 16m² floor plan — compact, not spacious — rooms are narrow-long
- Palette reference: Visual DNA v2.7 §12 — warm neutral tones, dark wood accents
- Hotel tier: boutique mid-range on West Lake — NOT luxury resort
- Authenticity principle: trustworthy impression over polished perfection
- Corresponds to room_2 from v2.3 DNA (ceiling: flat_white, lake view)
