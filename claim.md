# The Claim

This page walks through the top of the FORRT chain — three nanopublications
that together turn one sentence in [Soroye et al. 2020](https://doi.org/10.1126/science.aax8591) into
a structured, citable, machine-readable scientific claim.

## Why three nanopubs and not one?

FORRT chains separate the *act of citing* a paper from the *content of the
claim* and from *how that claim is being tested*. Each step strips away
context until what's left is the bare assertion that downstream Replication
Studies and Outcomes can target.

| Step | Template | What it is | Why it exists |
|---|---|---|---|
| 1 | Quote-with-comment | Verbatim quote from the paper + a personal comment + a citation | Anchors the chain in the paper, and lets the researcher say *why* this quote is worth replicating |
| 2 | AIDA sentence | A single Atomic-Independent-Declarative-Absolute version of the quote | Strips method language and hedging; what's left is what can be replicated |
| 3 | FORRT Claim | The structured claim with topic tags, type, and links back to the paper | The unit that Replication Studies test |

## 1. Quote with comment

The quote is from Soroye's Discussion / Conclusion section (page 3–4 of
the published paper):

> *Using a spatially explicit method of measuring climatic position and
> its change over time, we show that risks of bumble bee extirpation rise
> in areas where local temperatures more frequently exceed species'
> historical tolerances, whereas colonization probabilities in other areas
> rise as climate changes cause conditions to more frequently fall within
> species' thermal limits.*

**Personal comment** (the "why this matters" wrapped around the quote):

> Replicating this claim on independent data is the prerequisite for using
> it: once the mechanism is validated, the same pipeline can be projected
> onto future climate scenarios to anticipate where pollinator extirpation
> risk will rise, flag candidate climate refugia for conservation
> prioritisation, or be extended to other thermally-sensitive insect taxa.

<iframe src="https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RAQ9l3vNjaSUeYZ8A0wgrzDPEbQQXBbd8jMszJ8pBzoiw"
        width="100%" height="600" style="border:1px solid #ddd;border-radius:4px;"></iframe>

[View the Quote nanopub on Science Live →](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RAQ9l3vNjaSUeYZ8A0wgrzDPEbQQXBbd8jMszJ8pBzoiw)

## 2. AIDA sentence

The same idea, stripped to a single declarative sentence with no pronouns,
no method language, and no hedges:

> **Local extirpation rate in bumble bee species rises in areas where local
> temperatures more frequently exceed species-specific historically observed
> thermal tolerances.**

This is the form the Claim is structured around. Note what's gone: "we
show that…", the colonization mirror, the spatial-explicit framing.
What's left is a claim about the world.

<iframe src="https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RAdv1pQt3itwTZtddbsLz7LLprlCHj72bEF-oXQVeYtdU"
        width="100%" height="600" style="border:1px solid #ddd;border-radius:4px;"></iframe>

[View the AIDA nanopub on Science Live →](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RAdv1pQt3itwTZtddbsLz7LLprlCHj72bEF-oXQVeYtdU)

## 3. FORRT Claim

The structured claim. Type: *descriptive pattern* (an observed empirical
relationship between variables, in FORRT's controlled vocabulary). Topics
include bumblebee, climate change, pollinator decline, extinction, species
distribution. Cited authority: the Soroye paper.

This is the node both Replication Studies (Phase 2 + Phase 3) target via
the *Search for a FORRT claim* field on the Replication Study form.

<iframe src="https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RArj4912Wm6DO0Y-sR8KeaJsZUKrVcJHWArmINg-kaOhs"
        width="100%" height="600" style="border:1px solid #ddd;border-radius:4px;"></iframe>

[View the FORRT Claim nanopub on Science Live →](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/sciencelive/np/RArj4912Wm6DO0Y-sR8KeaJsZUKrVcJHWArmINg-kaOhs)

## What comes next

The same Claim is now tested two ways:

- [Phase 2](phase2.md) — does the Python re-implementation reproduce
  Soroye's result on Soroye's own data?
- [Phase 3](phase3.md) — does the same pipeline still detect the signal on
  independent Iberian GBIF data?
