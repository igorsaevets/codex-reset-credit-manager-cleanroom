# Strategic Review - 2026-07-26

## Inputs

- External reviewer 1: Muse Spark (`muse-spark-1.1`, tier `deep`)
- External reviewer 2: Gemini (`gemini-3.1-pro-high`)
- Independent source checks:
  - GitHub licensing docs
  - GitHub Terms of Service
  - OpenAI Terms of Use
  - OpenAI Codex app-server README

## What both reviewers supported

- Start with a private repository.
- Keep the first milestone read-only.
- Do not publish or reuse unlicensed upstream code.
- Treat environment-variable inheritance as a first-class security problem.
- Keep the existing local installation isolated and untouched.

## What I accepted after source checks

- GitHub docs say that without a license, default copyright applies and others
  may not reproduce, distribute, or create derivative works.
- GitHub Terms say public visibility allows viewing and forking through GitHub,
  not broad off-platform reuse.
- OpenAI Terms of Use explicitly forbid circumventing rate limits,
  restrictions, or safety measures.
- OpenAI's `codex app-server` README describes it as the interface Codex uses to
  power rich interfaces and documents the `--stdio` transport.

## Practical decision

This repository stays private and read-only for now. The current codebase is a
safe planning and hardening draft, not a public release candidate.

