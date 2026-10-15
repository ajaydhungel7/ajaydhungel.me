---
title: "I Use Obsidian as a Second Brain for Claude Code"
date: 2026-06-13
draft: true
author: Ajay Dhungel
description: "How I turned an Obsidian vault into a persistent memory layer that keeps Claude Code sharp across sessions."
tags: ["ai", "devops", "automation", "productivity"]
tech: ["claude", "obsidian"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Claude Forgets Everything

Every time you start a new Claude Code session, the slate is clean. It does not remember what you decided last week, why you made that architectural call, or what variants you rejected. You end up re-explaining the same context over and over, and if you forget to mention something, Claude makes decisions that contradict choices you already made and thought were settled.

I hit this constantly when I started using Claude Code to manage my CV tailoring workflow. I would open a session, Claude would help me tailor a resume for a company, and then the next session it had no idea any of that had happened. I wanted something more durable.

Obsidian had been growing in popularity and I wanted to see what the fuss was about. I decided to try it with Claude Code and see how it worked. What I ended up with was a structured memory layer that Claude reads and writes across sessions.

---

## What Obsidian Brings to This

Obsidian is a local-first markdown editor that stores everything as plain files on your machine. No proprietary format, no sync lock-in, just folders full of `.md` files. That simplicity is what makes it useful here.

Claude Code can already read files in your working directory. So if you point a Claude Code project at an Obsidian vault, you get a system where Claude can read any note you have written, update files as the work evolves, and carry knowledge forward into the next session. No MCP server required, no external APIs, no tokens flying off to a third party memory service.

---

## How the Vault Is Actually Structured

My vault is not a general-purpose knowledge base. It is purpose-built around one project: maintaining a master CV and tailoring it per job application.

The root has `CLAUDE.md`, which is where the real magic lives. This file is automatically loaded by Claude Code at the start of every session. It contains the workflow rules, the compilation commands, the decisions that are not up for re-litigation, and exactly what to do when I drop a job description in.

Then there is a `cv-wiki/` folder, which is Claude's managed memory. It has six files:

- `state.md` -- the current CV content, certifications, layout spec, everything about what the resume actually says right now
- `decisions.md` -- design and content decisions that have already been made (font choice, why XeLaTeX, why a certain job was removed)
- `variants.md` -- all the content variants: four summary variants, three skills variants, bullet variants per employer
- `companies.md` -- application tracking, one entry per company I have applied to
- `log.md` -- an append-only changelog, most recent first
- `index.md` -- a quick map of what lives where

The rest of the vault is the actual work: a master `resume.tex` that is never directly tailored, a `companies/` folder where each application gets its own subdirectory with the job description and a tailored copy, and a `configs/` folder for per-company variant selections.

---

## The Workflow in Practice

When I start a session, Claude reads `CLAUDE.md` and already knows the rules. When I paste a job description, it reads `cv-wiki/variants.md` to figure out which content variants match, creates a company folder, copies the master, tailors it, compiles it with XeLaTeX, and then updates three wiki files: the application log, the companies tracker, and the state file if anything changed.

The next session, all of that is still there. Claude can read `cv-wiki/log.md` and know exactly what was done and when. It can check `cv-wiki/decisions.md` before suggesting something that was already tried and rejected. It does not have to ask me why the Swostech job is not on the resume because that decision lives in the wiki.

That is the shift. Instead of me carrying the context in my head and re-explaining it every session, the vault carries it. Claude reads the vault. I just describe what I want done.

---

## Why It Works Well

Once I started using it, a few things stood out:

The **Terminal plugin** lets me run XeLaTeX compilation directly from inside Obsidian without switching contexts. I open a session, tailoring happens, PDF compiles, all from the same window.

The **graph view** tells you something useful even in a small vault. In mine, `index.md` sits at the center, connected to every wiki file -- log, state, variants, companies, decisions. `CLAUDE.md` floats as an orphan at the top, disconnected from everything. That is not a mistake. It is not a wiki note; it is a system instruction file. Seeing it sit outside the web is a good reminder of the distinction: `CLAUDE.md` is what Claude reads to know how to behave, and the wiki is what Claude reads to know what is true.

**Obsidian Sync** gives me a backup without any setup. The vault lives locally, but sync keeps it safe.

And critically, it is just files. No vendor lock-in. If I ever want to move this to a different system, every note is a markdown file I can take anywhere.

---

## Closing the Loop with a Custom Skill

One thing I built to make this work cleanly is a Claude Code skill called `/update-obs`. Skills in Claude Code are markdown files that live in `~/.claude/skills/` -- drop a file there and it becomes an invocable slash command in any session.

You run `/update-obs` at the end of a session and it syncs everything back into the wiki -- updates `state.md` to reflect what changed, appends a structured log entry to `log.md`, and updates the companies tracker if any applications were worked on.

The log entry format is simple: a date, a type (edit, structure, setup, company), a title, and bullet points of what changed. Nothing gets fabricated -- the rule is to only record what actually happened that session.

To make sure I never forget to run it, `CLAUDE.md` has a matching instruction:

```
## Last thing to do in every session
Run /update-obs to sync the wiki before ending the session.
```

What this gives you is a clean loop. The session opens with Claude reading the wiki to know the current state. The session ends with `/update-obs` writing the new state back. Next session, Claude picks up exactly where things left off.

Without that closer, the memory only works in one direction. You get continuity from reading but the wiki drifts out of sync as the actual work moves forward. The skill is what keeps the two in step.

---

## The Part That Surprised Me

I expected the session-to-session continuity to be the main win. That is real. But what I did not expect was how much better the decisions got over time.

Because `cv-wiki/decisions.md` captures not just what was decided but why, Claude can make judgment calls that are consistent with past reasoning. When I am considering whether to add a project, it can check whether that project fits the signal the CV is trying to send based on past decisions, not just the current session context. It has accumulated reasoning, not just accumulated facts.

That is closer to how memory actually works. And it came from keeping structured markdown files in a local vault.

---

That's all for now! If you are using Claude Code heavily and find yourself re-explaining the same project context every session, a structured Obsidian vault is worth the hour it takes to set up. Thank you for making it to the end.
