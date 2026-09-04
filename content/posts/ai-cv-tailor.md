---
title: "I Built an AI Pipeline That Tailors My CV From a Job Description"
date: 2026-09-04
draft: false
author: Ajay Dhungel
description: "How I built an AI-native CV tailoring pipeline where Claude reads a job description, makes tailoring decisions, and compiles a submission-ready PDF."
tags: ["ai", "automation", "productivity", "devops"]
tech: ["aws"]
cover:
  image: /imgs/post-008.png
  alt: AI CV tailoring pipeline diagram
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## The Problem With Tailoring a CV by Hand

Every job application wants something slightly different. One role leads with Kubernetes, another is all about Terraform, a third cares mostly about observability. If you're applying seriously you can't just fire off the same resume everywhere, but manually tailoring it for every company takes time and the results are often half-hearted anyway.

I wanted something better. Not a tool that does keyword stuffing, but one that actually reasons about the role and decides what to emphasize, what to cut, and how to frame things. So I built it.

---

## How I Used to Do It

My old workflow was a Google Doc. Open it, rewrite a few bullets for the role, export a PDF, send it. Simple enough, and it worked.

The problem I ran into was that after a few applications the document had drifted. Old edits from a previous role were still in there, I was not sure which version I had sent where, and the "master" was not really a master anymore. It was just the most recent thing I had submitted somewhere.

I wanted a cleaner setup where the master stayed clean and every tailored copy was generated rather than edited by hand. That is what this pipeline is.

---

## The Design Constraint That Made This Work

The core idea is a master resume that is never submitted directly.

`resume.tex` is the single source of truth. It contains everything about my experience, every bullet variant, every framing option. When targeting a specific role, Claude reads the job description, compares it against a variant library in `cv-data.json`, and builds a tailored copy under `companies/<company>/resume.tex`. The master stays untouched.

This separation matters. If you let your master drift with every application, you end up with a document that is trying to be everything at once and ends up being nothing in particular. The master is for completeness. The tailored copy is for the match.

---

## What cv-data.json Actually Does

The variant library is where the real content lives. For each experience entry I have multiple bullet variants, some that lead with the infrastructure angle, some that lead with automation, some that go deeper on observability or security. Different roles care about different things.

When Claude reads a job description, it pulls from this library rather than rewriting bullets from scratch. The variants were written once, carefully, and they hold up across applications. Claude's job is selection and arrangement, not generation.

The same logic applies to the summary and the title. I have a few variants there too. The JD determines which one fits.

---

## CLAUDE.md Is the Brain of the Workflow

Every Claude Code project can have a `CLAUDE.md` that is automatically loaded at the start of every session. Mine is where the workflow lives.

It tells Claude exactly how to run a tailoring pass: read the JD, check `cv-data.json` for matching variants, create the company folder, build the tailored `.tex`, compile with XeLaTeX, update the wiki. It covers constraints too, like when to trim to one page and which sections are never cut regardless of the role.

This means I do not have to re-explain the workflow every session. I paste a job description. Claude already knows what to do with it.

---

## The Wiki Keeps Decisions Alive

`cv-wiki/` is Claude's persistent memory across sessions. Six markdown files:

- `state.md` -- what the master resume actually says right now
- `decisions.md` -- design and content choices that are not up for re-litigation
- `variants.md` -- all the content variants, indexed and annotated
- `companies.md` -- application tracking, one entry per company
- `log.md` -- an append-only changelog, most recent first
- `index.md` -- a quick map of what lives where

The decisions file is the one I rely on most. It captures not just what was decided but why. When I am considering whether to add a project, Claude can check whether it fits the signal the CV is sending based on past reasoning, not just current session context. That accumulated judgment is what makes the system feel coherent over time rather than just competent in the moment.

---

## What the Actual Workflow Looks Like

In practice it is this:

1. Paste the job description into the Claude Code session
2. Claude reads the JD and `cv-data.json`
3. Claude creates `companies/<company>/resume.tex` with the tailored content
4. Compiles to PDF with XeLaTeX
5. Wiki is updated: log entry, application status, any new variant decisions

I review the PDF before it goes anywhere. The AI drafts, I approve. Nothing gets submitted without a human reading it first, which is the right call. Claude's judgment on what to emphasize is usually good. Its judgment on whether a company is worth applying to is my call.

And just like that, what used to take 30-40 minutes of careful editing takes a few minutes of review.

---

## The Repo

Everything is open on GitHub at [ajaydhungel7/ai-cv-tailor](https://github.com/ajaydhungel7/ai-cv-tailor). The README covers the setup and the workflow in detail. The `CLAUDE.md` in that repo is the actual one I use, which might be the most useful thing to look at if you're thinking about adapting this for your own situation.

It requires Claude Code and XeLaTeX. Both are free to install.

---

That's all for now! If you're applying for roles and find yourself doing the same tailoring work over and over, this is worth a few hours to set up. Thank you so much for making it to the end.
