# How to Create a New Project

A "project" in VENHO AI Studio is a named collection of subjects (room types, locations, characters).
The first project is `venho_hotel`. Adding a second project does not touch any core engine code.

---

## Step 1 — Create the project config folder

```bash
mkdir -p config/projects/<project_name>/subjects
```

Example for a new cafe project:

```bash
mkdir -p config/projects/the_coffee_lab/subjects
```

---

## Step 2 — Create at least one subject schema

Copy an existing schema as starting point:

```bash
cp config/projects/venho_hotel/subjects/lake_view_room.yaml \
   config/projects/the_coffee_lab/subjects/interior.yaml
```

Then edit `interior.yaml`:
- Set `schema_id`, `display_name`, `description`
- Adjust `aggregation_keys` for your subject
- Update `forbidden_defaults` if needed

See [`how_to_create_new_subject.md`](how_to_create_new_subject.md) for schema structure.

---

## Step 3 — Create the media folder

```bash
mkdir -p data/projects/<project_name>/media/<subject_name>
```

Add images. Per §2.1 rule: ONE subject per folder.

---

## Step 4 — Run Mode B

```bash
venho vision observe --mode b \
  --project the_coffee_lab \
  --subject interior \
  --input data/projects/the_coffee_lab/media/interior
```

Output goes to:
```
data/projects/the_coffee_lab/knowledge/THE_COFFEE_LAB_INTERIOR_DNA.md
data/projects/the_coffee_lab/knowledge/THE_COFFEE_LAB_INTERIOR_DNA.json
```

---

## Step 5 — (Optional) Add an overlay

```bash
touch config/projects/the_coffee_lab/subjects/interior.overrides.yaml
```

See [`how_to_use_overrides.md`](how_to_use_overrides.md) for overlay format.

---

## Checklist

- [ ] `config/projects/<project>/subjects/<subject>.yaml` created
- [ ] `data/projects/<project>/media/<subject>/` contains images (one tier per folder)
- [ ] Mode B runs successfully
- [ ] DNA file looks correct
- [ ] Overlay created (if needed)
