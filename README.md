# Phase 1 — Component Data Model

This repository contains the Phase 1 deliverables for the Component data model exercise.

## Overview

Phase 1 focuses on defining the physical structure of object layouts and simple
serialization logic. No server logic, CLI, or menus are required — just a clean
in-memory model and manual verification via a small script.

## Files

- `models/component.py` — `Component` class with `id` (int), `name` (str), `owner` (str),
  and `status` (defaults to "Available"). Includes `to_dict()` and `from_dict()`.
- `manual_test.py` — basic script that instantiates a `Component`, serializes it to a
  dictionary, deserializes back to an object, and prints outputs to the console.

## What to Submit (required)

- The core data model file: `models/component.py`.
- Class properties mapping: `id`, `name`, `owner`, `status`.
- Serialization methods: `to_dict()` and `from_dict()`.
- A manual testing script: `manual_test.py` demonstrating instantiation and
  dictionary conversion.

You are welcome to add extras (tests, validation, additional helpers), but the
items above are necessary to submit.

## How to Run the Manual Test

From the project root (where `manual_test.py` lives), run:

```bash
python manual_test.py
```

You should see the original object printed, the dictionary representation, and
the object recreated from the dictionary.

## Git Submission (example)

This example shows a minimal sequence you can use to prepare and push Phase 1.
Adjust remote and branch names as needed.

```bash
git init
echo "__pycache__/" >> .gitignore
echo "gear.json" >> .gitignore
git add .gitignore models/component.py manual_test.py README.md
git commit -m "Phase 1 Complete: Component model, serialization, and tests"
git branch -M main
# add your remote, e.g.:
# git remote add origin git@github.com:yourname/yourrepo.git
# git push -u origin main
```

## Notes

- The `Component` model is intentionally simple to make Phase 1 focused and
  reviewable. Keep names and types stable; follow-up phases will add behavior
  and persistence.

Warm regards,

Head of Team Coding and Innovation
