# Rapport design-scout — fde-kit, itération 3 (BHV-4, BHV-5, BHV-6, BHV-8)

> **Statut : rapport, aucune décision.** Rôle `design-scout` (`lab/plugin/agents/design-scout.md`) :
> « You decide nothing, you document proven patterns. […] You never write into design.md directly:
> you hand your report to the Owner. » Rédigé en session 5 (2026-11-14, nuit, sans l'Owner) dans la
> session Claude Code, **sans** appel d'agent facturé ni recherche web.
>
> Base : `main` = `5b8d424` (PR #3). Spec fde-kit 0.8.0 (validée), design 0.6.0 (validé, couvre
> les itérations 1-2 seulement : « Les itérations 3 […] seront conçues à leur tour, par amendement
> de ce document »). Numérotation : suite de design §2.1 (I-1..I-25) et §2.2 (E-1..E-17).

## Périmètre

Problèmes d'architecture posés par l'itération 3, tirés de la spec :

| # | Problème | Source spec |
|---|---|---|
| P1 | Déduire la phase courante (spec → design → plan → build → review → merge) | BHV-4 (« des `status:` du frontmatter et de `.runs/state.json` ») |
| P2 | Critères de sortie par phase : spec-lint, goldfish, design-lint, plan-lint, build, review | BHV-4 (tableau) |
| P3 | Classer un signal d'échec en route R1..R7 | BHV-5, BHV-5c |
| P4 | Proposition écrite par le moteur (`.runs/<id>-<route>.md`), appliquée après décision signée | INV-3, R2..R5 |
| P5 | Budget fini par route, escalade humaine | INV-4, BHV-5a |
| P6 | Reprise sur un graphe amendé sans rejouer les `done` hors delta | BHV-5b |
| P7 | Reset ciblé des dépendants (recoupement de fichiers ou d'IDs) | BHV-6, BHV-6a/b |
| P8 | Aucun agent ne modifie `spec.md`/`design.md` pendant un run | INV-10 |
| P9 | Test goldfish : spec masquée, deux lecteurs isolés, canari, comparaison | BHV-8, BHV-8a..e, INV-12 |

## Piste 1 — Patterns internes (ce repo, vérifiés sur `5b8d424`)

| # | Problème | Pattern interne (fichier:ligne) | Réutilisation possible | À ne pas reproduire |
|---|---|---|---|---|
| I-26 | P1 frontmatter | `lab/engine/plan.py:37` `parse_tasks_md` (frontmatter + nœuds) ; `orchestrate.py:1314` refuse un plan non `approved` | Même lecteur pour `spec.md`/`design.md` (`status: validated`) | — |
| I-27 | P1 état de run | `orchestrate.py:1357-1395` : `state.json` relu au démarrage, tolérant à un fichier tronqué (L9), écrit par `atomic_write_json` | Source « done » d'un `lab next` | `state.json` est gitignoré : perdu avec l'environnement (lab-fix 38) |
| I-28 | P1/P6 état dérivé de git | `planlint.py:63-72` `committed_task_ids` : tâches « done » lues dans `git log` (sujet canonique) — « reproductible depuis un checkout frais, contrairement à `state.json` » | Alternative ou complément à I-27 (BHV-4 nomme `state.json` : un changement de source = amendement) | — |
| I-29 | P2 plan-lint | `planlint.py:164` `validate` (DAG, IDs, recoupements, politique) | Critère de sortie « plan » tel quel | — |
| I-30 | P2 spec/design | `content_guard.py:60` `extract_content` (substance vs forme) ; `planlint.py` vérifie déjà les IDs de spec cités par le plan | Base d'un spec-lint (IDs uniques, couverture EVAL) | **Aucun spec-lint ni design-lint n'existe** (aucun fichier, aucune recette) : à concevoir |
| I-31 | P2 build | `orchestrate.py:898` `_run_task_attempts` → verify → `_eval_gate` (anti-empty-gate, couverture) → `scoped_commit` | Critère « build » existant | — |
| I-32 | P2 review | `orchestrate.py:1040` `run_review` (panel, rapport `.runs/CP-n-review.md` `:1089`), `:1110` `wait_checkpoint` | Critère « review » existant | — |
| I-33 | P3 signal | `orchestrate.py:950` `re.search(r"STATUS:\s*(done|blocked)([^\n]*)")` ; prompt `:718` « STATUS: blocked — <reason, e.g. OQ-3> » | Point unique où classer R3/R4/R5 (la catégorie est aujourd'hui du texte libre) | Pas de catégorie structurée : BHV-5c exige « non classable ⇒ human » |
| I-34 | P3 R1 | `orchestrate.py:908` boucle `for attempt in range(1, MAX_EVAL_RETRIES + 1)` ; `MAX_EVAL_RETRIES` lu de la politique `:393` | R1 existe déjà | — |
| I-35 | P3 R7 | `orchestrate.py:1093` `parse_rejection`, `:1498-1512` compteur `rejections`, rework « OWNER REVIEW FEEDBACK » injecté | R7 existe déjà (sans reset des dépendants) | Compteur en mémoire : remis à zéro à chaque redémarrage du moteur |
| I-36 | P4 écrit par le moteur | `orchestrate.py:1044-1089` : le moteur écrit le rapport de revue dans `.runs/` ; `.gitignore` garde `.runs/*-review.md` versionnés « pour l'audit » | Même forme pour `.runs/<id>-<route>.md` | — |
| I-37 | P4 décision signée | `approvals.py:55` `sign`, `:79` `verify` (HMAC) ; `approve.sh`/`reject.sh` | Signature d'une proposition (même jeton que les CP) | — |
| I-38 | P4/P8 OQ d'agent | `orchestrate.py:715` : le prompt de l'implementer dit « record the question (OQ-n format) in spec.md §8 and end blocked » | — | **Contredit INV-10 et R3** (« le **moteur** l'écrit dans `.runs/<Tn>-OQ.md` ») ; cause directe du lab-fix 34 |
| I-39 | P5 routes | `policy.py:5` : « `[overrides.routes]` valide R1..R7 (INV-3) mais n'est appliqué qu'à partir de l'itération 3 » ; `:113-122` validation | Lecture des modes de route déjà en place | — |
| I-40 | P5/BHV-5a containment | `plan.py:145` `skip_dependents` ; `orchestrate.py:1479`, `:1504` | Escalade = sous-arbre `skipped`, autres branches continuent | — |
| I-41 | P7 recoupement | `plan.py:140` `paths_overlap` ; `plan.py:120` `ancestors` ; `Node.implements` | Calcul des dépendants à rouvrir (fichiers **ou** IDs) | — |
| I-42 | P8 commit scopé | `orchestrate.py:550` `scoped_commit` ; PR #10 : ne stage plus que `tasks.md` dans le dossier de la feature (INV-10) | Moitié « commit » d'INV-10 | La moitié « la tâche échoue si le working tree touche spec/design » n'existe pas |
| I-43 | P9 essai isolé | `eval_models.py:102` `call_model` (cwd dédié), `:148` `tempfile.mkdtemp(prefix="labeval-")` ; fichier de rôle copié dans le cwd de l'essai (`4bf2b48`) | Répertoire temporaire par lecteur | Lab-fix 19 : `--plugin-dir`/`--settings` restent des chemins du kit dans l'argv |
| I-44 | P9 lecteurs | `lab/models/registry.toml` `[roles]` ; `registry.py` `role_default` | Lecteur implementer = rôle `implementer` | **Aucun rôle `goldfish`** dans le registre (BHV-8e prévoit son absence) |
| I-45 | P9 comparaison | `evals/behavioral/cases.py:60` `verdict`, `:89-162` checkers ; `eval_models.py:276/294` contrat API / logique | Forme « checker → (ok, détail) » | Aucun comparateur YAML champ par champ (BHV-8a) |

## Piste 2 — Références externes : non faite

Pas de recherche web ni d'appel d'agent facturé dans cette session (règle de l'Owner : confirmer
toute dépense ou action extérieure). Problèmes pour lesquels une référence externe reste à
chercher, ou à déclarer « sans référence — ADR délibéré » :

- P3 : classement d'échecs en routes avec budgets (orchestrateurs de workflows).
- P6 : reprise d'un DAG amendé sans rejouer les nœuds terminés.
- P9 : isolement prouvé d'un appel de modèle (canari), comparaison normalisée de sorties YAML.

## Questions pour l'Owner (aucune n'est tranchée ici)

1. État de run : `state.json` (I-27, nommé par BHV-4), git (I-28), ou les deux ? Lié aux lab-fix 37 et 38.
2. Catégorie de `STATUS: blocked` : texte libre (I-33) ou forme structurée (`OQ` / `ADR` / `scope`) pour R3/R4/R5 ?
3. I-38 : le prompt de l'implementer écrit les OQ dans `spec.md`. Le changer touche le prompt d'un rôle (boucle EVOLUTION) — maintenant ou dans l'itération 3 ?
4. Compteur de rejets en mémoire (I-35) : persistant pour que `max_cp_rejects` survive à un redémarrage ?
5. spec-lint et design-lint n'existent pas (I-30) : nouvelles recettes, ou extension de plan-lint ?
6. Rôle `goldfish` (I-44) : quel modèle `fast` du registre, et faut-il une campagne avant ?
