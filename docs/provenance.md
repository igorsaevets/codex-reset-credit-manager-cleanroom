# Provenance

## Current status

This repository is a private draft that was written from scratch after prior
evaluation work on an unlicensed third-party repository.

## Why the repository is private

Because the initial analyst previously inspected that unlicensed third-party
codebase, this repository should not be described as a formal legal clean-room
deliverable yet. Keeping it private preserves room for one of these next steps:

1. a separate reimplementation from a public-behavior spec by an isolated
   implementer, or
2. a deliberate human review that accepts the remaining derivative-risk
   exposure before publication.

## What we intentionally avoided

- no copied source text
- no copied file inventory
- no copied function names
- no copied scheduler offsets
- no copied installation layout

## What is still true

High-level product requirements can overlap:

- Windows-first local execution
- strong secret handling
- read-only first
- no live consume in tests
- safe scheduler behavior

Those are problem constraints, not protected source text.

