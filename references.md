# References

## The replicated paper

Soroye P., Newbold T., Kerr J. (2020). *Climate change contributes to widespread declines among bumble bees across continents*. **Science** 367(6478):685–688. [https://doi.org/10.1126/science.aax8591](https://doi.org/10.1126/science.aax8591) · [Wikidata Q89582023](https://www.wikidata.org/wiki/Q89582023)

## Data sources

- **Soroye et al. data repository** (continental *Bombus* occurrences, R scripts, CRU TS climate). Figshare. [https://doi.org/10.6084/m9.figshare.9956471](https://doi.org/10.6084/m9.figshare.9956471)
- **GBIF Occurrence Download** (Iberian *Bombus*, 36 560 records, ES + PT, georeferenced, no geospatial issues, accessed 2026-04-25). License CC-BY-NC 4.0. [https://doi.org/10.15468/dl.3frmsq](https://doi.org/10.15468/dl.3frmsq)
- **CRU TS 3.24.01 monthly climate** (Harris et al. 2014). [https://doi.org/10.1002/joc.3711](https://doi.org/10.1002/joc.3711)

## This work

- **Source code archive (Zenodo concept DOI, resolves to latest version):** [10.5281/zenodo.19756173](https://doi.org/10.5281/zenodo.19756173)
- **Source code v0.2.1:** [10.5281/zenodo.19762723](https://doi.org/10.5281/zenodo.19762723)
- **Docker container image v0.2.1:** [10.5281/zenodo.19762828](https://doi.org/10.5281/zenodo.19762828)
- **Repository:** [github.com/annefou/weatherxbiodiversity](https://github.com/annefou/weatherxbiodiversity)

## The 9-nanopub chain

| # | Step | URI |
|---|---|---|
| 1 | Quote-with-comment | [`RAQ9l3vNjaSUeYZ8A0wgrzDPEbQQXBbd8jMszJ8pBzoiw`](https://w3id.org/sciencelive/np/RAQ9l3vNjaSUeYZ8A0wgrzDPEbQQXBbd8jMszJ8pBzoiw) |
| 2 | AIDA sentence | [`RAdv1pQt3itwTZtddbsLz7LLprlCHj72bEF-oXQVeYtdU`](https://w3id.org/sciencelive/np/RAdv1pQt3itwTZtddbsLz7LLprlCHj72bEF-oXQVeYtdU) |
| 3 | FORRT Claim | [`RArj4912Wm6DO0Y-sR8KeaJsZUKrVcJHWArmINg-kaOhs`](https://w3id.org/sciencelive/np/RArj4912Wm6DO0Y-sR8KeaJsZUKrVcJHWArmINg-kaOhs) |
| 4 | Phase 2 Replication Study (Robustness) | [`RADLcvxDglyzEnEfAo9e6RfnXQ_YK3v_gJcnWLVBkIbP4`](https://w3id.org/sciencelive/np/RADLcvxDglyzEnEfAo9e6RfnXQ_YK3v_gJcnWLVBkIbP4) |
| 5 | Phase 2 Replication Outcome — Validated, High | [`RABeytsVYYMfRz_Jb3O__naWSg8Z63WTnQsofidkdrVvk`](https://w3id.org/sciencelive/np/RABeytsVYYMfRz_Jb3O__naWSg8Z63WTnQsofidkdrVvk) |
| 6 | Phase 3 Replication Study (Replicability) | [`RA51YMjEluCKKQWWIuB9_SBU88dgCaonVuqtS4CspPiUE`](https://w3id.org/sciencelive/np/RA51YMjEluCKKQWWIuB9_SBU88dgCaonVuqtS4CspPiUE) |
| 7 | Phase 3 Replication Outcome — Validated, High | [`RAIylrhtnfTH_vtp1nTDVAiGsv2u_Ea4Uvh35DrGySuWs`](https://w3id.org/sciencelive/np/RAIylrhtnfTH_vtp1nTDVAiGsv2u_Ea4Uvh35DrGySuWs) |
| 8 | CiTO — Phase 2 confirms Soroye 2020 | [`RAdvbQt3vXT0HpyNYdwwMBs8fVnmyv5KWFT0eXfVTDXg0`](https://w3id.org/sciencelive/np/RAdvbQt3vXT0HpyNYdwwMBs8fVnmyv5KWFT0eXfVTDXg0) |
| 9 | CiTO — Phase 3 confirms Soroye 2020 | [`RApCQTLMP8h0jDYF9ggWU6lMTW7a_KG5_Jygbsx0aTpIo`](https://w3id.org/sciencelive/np/RApCQTLMP8h0jDYF9ggWU6lMTW7a_KG5_Jygbsx0aTpIo) |

## Frameworks and standards

- **FORRT — Framework for Open and Reproducible Research Training.** [forrt.org](https://forrt.org/)
- **Nanopublications.** [nanopub.net](https://nanopub.net) · published via [knowledgepixels.com](https://knowledgepixels.com)
- **Science Live platform.** [platform.sciencelive4all.org](https://platform.sciencelive4all.org)
- **CiTO — Citation Typing Ontology.** [https://sparontologies.github.io/cito/current/cito.html](https://sparontologies.github.io/cito/current/cito.html)
- **AIDA sentences.** Atomic, Independent, Declarative, Absolute claim format.

## Tooling

- Python 3.12 · `xarray`, `pandas`, `statsmodels`, `scipy` · [environment.yml](https://github.com/annefou/weatherxbiodiversity/blob/main/environment.yml)
- `pygbif` for GBIF download API access
- `pyproj` for cylindrical-equal-area projection
- MyST + Jupyter Book for this site
