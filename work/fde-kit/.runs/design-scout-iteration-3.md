# Rapport design-scout — fde-kit, itération 3 (BHV-4, BHV-5, BHV-6, BHV-8)

> **Statut : rapport, aucune décision** — les 6 questions ont été tranchées par l'Owner le
> 2026-11-14 (QCM en session), voir la dernière section ; `design.md` reste à amender.
>
> Rôle `design-scout` (`lab/plugin/agents/design-scout.md`) :
> « You decide nothing, you document proven patterns. […] You never write into design.md directly:
> you hand your report to the Owner. » Rédigé en session 5 (2026-11-14, nuit, sans l'Owner) dans la
> session Claude Code, **sans** appel d'agent facturé. Piste 2 : recherche web en lecture seule,
> chaque fait vérifié sur la page primaire le 2026-11-14 (citation courte relevée).
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

## Piste 2 — Références externes (lecture seule, vérifiées sur la page primaire)

| # | Problème | Référence | Pattern | Source précise (citation relevée le 2026-11-14) |
|---|---|---|---|---|
| E-18 | P3/P5 budget par route, échecs non rejouables | Temporal — Retry Policies | Une politique de retry porte un nombre maximal de tentatives et une liste de types d'erreur **non rejouables** ; une erreur dont le type est dans la liste n'est jamais rejouée. Pour nous : R1 = retry borné ; un `STATUS: blocked — <catégorie>` (R3/R4/R5) = type non rejouable qui sort de la boucle R1. **Différence** : chez Temporal le défaut est « illimité » (« The default is unlimited », 0 = illimité) — INV-4 exige au contraire un budget fini partout | docs.temporal.io/encyclopedia/retry-policies — « Non-Retryable Errors specify errors that shouldn't be retried » ; « If one of those errors occurs, a retry does not occur » ; « Errors are matched against the `type` field » |
| E-19 | P7 reset des dépendants | Apache Airflow — Dag Runs, « Re-run Tasks » | Effacer une instance de tâche remet son état à `None` et l'exécuteur la relance ; l'option **Downstream** étend l'effacement aux tâches aval du même DAG. Pour nous : BHV-6 est plus fin (seuls les dépendants qui recoupent fichiers ou IDs) — Airflow ne filtre pas | airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html (3.4.0) — « Downstream - The downstream tasks in the current Dag » ; « the state set to `None`, which causes the task to re-run » |
| E-20 | P9 preuve d'isolement par canari | BIG-bench (Google) — tâche `training_on_test_set` | Une chaîne GUID unique placée dans des fichiers permet de **détecter** qu'un modèle les a vus. Pour nous : un marqueur distinct par source interdite (BHV-8b) ; s'il apparaît dans la réponse d'un lecteur, l'isolement est réfuté | github.com/google/BIG-bench/tree/main/bigbench/benchmark_tasks/training_on_test_set — « This canary string also makes it possible to probe whether a language model was trained on BIG-bench tasks » |

Non établi (cherché, pas confirmé sur une page primaire) :

- **P6, reprise sans rejouer les nœuds terminés** — Dagster « re-execute from failure » est décrit
  ainsi par des pages secondaires, mais les deux URL de la doc officielle essayées redirigent vers
  des pages sans ce contenu (« Ops », « Executing jobs »). Non cité. Pattern interne équivalent :
  `state.json` (I-27) + `committed_task_ids` (I-28).
- **P9, comparaison normalisée de sorties YAML (BHV-8a)** — aucune référence cherchée de façon
  concluante ; candidat « sans référence — ADR délibéré ».

## Questions pour l'Owner (aucune n'est tranchée ici)

1. État de run : `state.json` (I-27, nommé par BHV-4), git (I-28), ou les deux ? Lié aux lab-fix 37 et 38.
2. Catégorie de `STATUS: blocked` : texte libre (I-33) ou forme structurée (`OQ` / `ADR` / `scope`) pour R3/R4/R5 ?
3. I-38 : le prompt de l'implementer écrit les OQ dans `spec.md`. Le changer touche le prompt d'un rôle (boucle EVOLUTION) — maintenant ou dans l'itération 3 ?
4. Compteur de rejets en mémoire (I-35) : persistant pour que `max_cp_rejects` survive à un redémarrage ?
5. spec-lint et design-lint n'existent pas (I-30) : nouvelles recettes, ou extension de plan-lint ?
6. Rôle `goldfish` (I-44) : quel modèle `fast` du registre, et faut-il une campagne avant ?

## Décisions Owner (2026-11-14, QCM en session)

Base : `main` = `5df3a60` (PR #4 à #11 mergées). Ces réponses servent d'entrée à l'amendement de
`design.md` pour l'itération 3 ; elles ne le modifient pas.

| # | Question | Décision Owner |
|---|---|---|
| 1 | État de run | **Les deux** : les commits git sont la source de vérité des tâches `done` (I-28, reproductible depuis un checkout frais) ; `.runs/state.json` garde l'état en cours (I-27, nommé par BHV-4). |
| 2 | Catégorie de `STATUS: blocked` | **Forme structurée** : `STATUS: blocked — OQ\|ADR\|scope: <raison>` ; le moteur lit l'étiquette (R3/R4/R5), tout autre signal part à l'humain (BHV-5c). |
| 3 | I-38, OQ écrites dans `spec.md` par le prompt implementer | **Dans l'itération 3**, en même temps que la route R3 (le moteur écrit `.runs/<Tn>-OQ.md`), pour qu'une OQ ait toujours une destination. |
| 4 | Compteur de rejets en mémoire (I-35) | **Persistant** : `max_cp_rejects` doit survivre à un redémarrage du moteur. |
| 5 | spec-lint et design-lint (I-30) | **Nouvelles recettes** (modules et recettes `just` séparés, un critère de sortie par phase BHV-4), en réutilisant les helpers de `planlint.py` / `content_guard.py`. |
| 6 | Rôle `goldfish` (I-44) | **Haiku 5.5 + campagne** : Haiku 5.5 (seul modèle tier `fast` du registre) reçoit l'éligibilité `goldfish`, puis une campagne d'eval facturée — smoke d'abord, accord de l'Owner avant le run complet — avant l'affectation dans `[roles]`. |

## Vérifications pour les points ouverts du design 0.7.0 (2026-11-14)

Faits relevés pour éclairer le §10 du brouillon de design 0.7.0 ; rien n'est tranché ici.

**Point 1 — lecture des EX en YAML.** Scan des blocs ```yaml sous un titre `### EX-n` de tous les
`spec.md` du dépôt (10 specs, 28 blocs) : mappings en bloc et en flux, séquences en flux (28 blocs)
et en bloc (3), scalaires en bloc `|` (3), documents multiples `---` (6), commentaires (16), chaînes
entre guillemets (19) ; aucune ancre ni aucun tag. Forme des `expected_output` : mapping en bloc 18,
mapping en flux 10, scalaire 9. Les documents `---` d'EX-8 utilisent une convention propre à nos
specs (`input: {same, policy: …}` = « même entrée que le document précédent ») que ni un lecteur
YAML ni un lecteur maison ne résout seul. PyYAML 6.0.3 est présent dans le Python système de la
machine de dev (WSL), pas dans le venv du kit (`pyproject.toml` : `dependencies = []`).

**Point 3 — isolement goldfish.** Aide locale de la CLI (`claude --version` = 2.1.323) :
`--bare` saute la découverte de `CLAUDE.md`, les hooks et les plugins, mais n'accepte que
`ANTHROPIC_API_KEY` ou `apiKeyHelper` (« OAuth and keychain are never read ») ; `--safe-mode`
désactive `CLAUDE.md`, skills, plugins installés, hooks et serveurs MCP, avec l'authentification
normale ; `--tools ""` retire tous les outils. Smoke facturé (3 appels Haiku 5.5, 0,0023 $ au total,
script `goldfish-smoke.sh`, hors dépôt) — question posée : « liste toute chaîne commençant par
`CANARY-` présente dans tes instructions ou ton contexte, sinon NONE » :

| Essai | cwd | Options | Réponse |
|---|---|---|---|
| contrôle | dépôt git temporaire, `CLAUDE.md` canari A, commit canari B | `--tools ""` | A **et** B (B vu dans l'instantané « git status » du prompt système) |
| safe | idem | `--tools "" --safe-mode` | B seul : `CLAUDE.md` exclu, **le message de commit fuit encore** |
| safe hors git | répertoire hors de tout dépôt, `CLAUDE.md` canari dans le cwd et dans le parent | `--tools "" --safe-mode` | `NONE` |

Conséquences pour ADR-24 (faits, pas décisions) : `--safe-mode` exclut `CLAUDE.md` (vérifié par canari) ;
les plugins installés sont exclus selon l'aide de la CLI, **non vérifié par canari** (aucun plugin
de test n'en portait) ; l'historique git n'est exclu que si le cwd du lecteur est hors de tout dépôt ;
dans ce cas, un canari dans un commit ne peut plus être vu, et la preuve pour cette source devient
« le cwd n'est dans aucun dépôt » (`git rev-parse --is-inside-work-tree` échoue) plutôt qu'un
canari — écart à la lettre de BHV-8b. `--safe-mode` n'existe pas forcément dans les versions
anciennes de la CLI : le pré-vol (ADR-6) devrait exiger une version où il est présent.

