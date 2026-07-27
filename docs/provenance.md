# Provenance

## Current status

This repository is a public read-only MVP that was written independently after
earlier evaluation work on an unlicensed third-party repository.

## What this repository does and does not claim

This project is published under the MIT License, but it should not be described
as a formally isolated legal clean-room deliverable.

Why that caveat remains:

- earlier evaluation included reading an unlicensed third-party repository
- a formal clean-room claim would require stricter separation than this project
  can honestly represent
- public release does not remove the need for transparent provenance wording

## What the public release means

Making the repository public means the code is openly visible and MIT-licensed
for reuse on the terms of that license. It does not mean:

- that the project is a full automation tool
- that the project bypasses rate limits
- that the project is certified as a strict clean-room implementation

## What we intentionally avoided

- no copied source text
- no copied file inventory
- no copied function names
- no copied scheduler offsets
- no copied installation layout

## What is still true

High-level product requirements can overlap across independent tools:

- Windows-first local execution
- strong secret handling
- read-only first
- no live consume in tests
- safe scheduler behavior

Those are problem constraints, not protected source text.

## Future publication options

If stronger provenance posture is needed later, there are still two reasonable
paths:

1. keep this repository public but continue presenting it as an independently
   written public preview with an explicit caveat, or
2. create a stricter specification-first reimplementation process with stronger
   separation and publish that result as the higher-assurance successor
