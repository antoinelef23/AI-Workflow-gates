---
type: spec
feature: fde-kit
version: 0.1.0
status: draft            # draft | validated | superseded
owner: Antoine (Owner)
validated_by:            # vide tant que draft — itération en cours sur les OQ §8
---

# Spec — Kit FDE portable : workflow agentique templatisé, profils d'organisation, retours arrière routés

## 1. Intent

Un FDE arrive sur une nouvelle mission **avec son propre outillage** : son SDLC agentique
(moteur, agents, skills, garde-fous) doit s'installer dans le projet client en quelques
minutes, au **niveau de contrôle adapté à l'organisation** (FDE seul sur un POC, squad
mixte, environnement régulé), sans réécrire le workflow. Une fois le plan approuvé, le
workflow **enchaîne les phases seul** entre deux décisions humaines et, quand un agent
n'atteint pas son objectif, **renvoie l'échec vers l'artefact responsable** (code → plan →
design → spec) au lieu de simplement réessayer ou de s'arrêter. Chaque mission
**rend le kit meilleur** : ses retours (anonymisés) alimentent la boucle d'évolution.

**Target KPI :**
- Bootstrap d'un projet vierge jusqu'au premier `lab next` vert : non mesuré aujourd'hui
  (copie manuelle des templates + `--project`) → **≤ 30 min**.
- Garde-fous du kit actifs dans une instance externe : **0 garanti aujourd'hui** (aucun
  `--settings` transmis en mode `--project`) → **100 %** (INV-1).
- Interventions humaines hors checkpoints prévus, par feature : baseline à mesurer (OQ-8).

## 2. Glossary

| Business term | Canonical name (code) | Definition |
|---|---|---|
| Kit | `kit` | L'outillage versionné du FDE : moteur (`lab/engine`), agents, skills, hooks, templates, registry, profils |
| Instance | `instance` | Un projet client bootstrapé par le kit : `work/`, code, evals, `.lab/lab.toml` |
| Profil d'organisation | `policy_profile` | Jeu nommé de réglages de garde-fous (retries, densité de checkpoints, sandbox, panel, budget, routes) |
| Plancher | `policy_floor` | Profil minimal imposé par l'organisation ; une instance peut le durcir, jamais l'assouplir |
| Politique effective | `effective_policy` | Résultat de la fusion plancher ⊕ overrides de l'instance, clé par clé |
| Phase | `phase` | Étape du SDLC : `spec` → `design` → `plan` → `build` → `review` → `merge` |
| Critère de sortie | `exit_gate` | Check mécanique qui conditionne la transition vers la phase suivante |
| Signal d'échec | `failure_signal` | Événement classé émis quand un agent n'atteint pas son objectif (eval rouge, STATUS blocked, verdict BLOCK…) |
| Route d'échec | `failure_route` | Règle déclarative : signal → phase cible → mode (`auto` / `proposal` / `human`) → budget de boucles |
| Retour arrière | `backtrack` | Transition vers une phase amont déclenchée par une route d'échec |
| Delta de plan | `plan_delta` | Diff de `tasks.md` limité aux nœuds non démarrés, soumis à une approbation signée distincte |
| Retro | `retro_record` | Résumé anonymisé d'un run (compteurs, durées, coûts, modèles, routes empruntées) exportable vers le kit |

## 3. Invariants

- **INV-1** — Les garde-fous du kit (denies `.approvals/` et `.runs/`, eval gate `Stop`/`SubagentStop`,
  règles dures de CLAUDE.md, approbations signées fail-closed) MUST être actifs à l'identique, que
  le run s'exécute dans le repo du kit ou dans une instance externe — y compris une instance sans
  `.claude/`.
- **INV-2** — Une instance MUST NOT assouplir une clé sous son plancher : pour chaque clé,
  `effective_policy` = la valeur la plus stricte entre plancher et override.
- **INV-3** — Un retour arrière MUST NOT modifier un artefact humain (`spec.md`, `design.md`, un
  `tasks.md` au statut `approved`) : il produit une **proposition** (`.runs/<id>-<route>.md` +
  notification), appliquée seulement après décision humaine signée.
- **INV-4** — Chaque route d'échec a un budget de boucles fini ; budget épuisé ⇒ escalade humaine.
  Aucun cycle de retour arrière ne peut boucler indéfiniment.
- **INV-5** — Le merge reste humain dans **tous** les profils ; aucune clé de profil ne peut le
  rendre `auto`.
- **INV-6** — Un `retro_record` MUST NOT contenir de nom propre client/brand, de chemin d'asset ni
  de contenu de spec : uniquement des IDs, compteurs, durées, coûts, modèles, versions, noms de
  routes. Il passe `brand_guard`.
- **INV-7** — Une instance épingle la version du kit (`.lab/lab.toml`) ; tout upgrade du kit est
  un commit explicite de l'instance, jamais une dérive silencieuse.

## 4. Behaviors

### BHV-1 — Bootstrap d'une instance (`lab init <project> --profile <p>`)
- **Given** un repo git sans le kit
- **When** le FDE lance `lab init <project> --profile squad`
- **Then** sont créés : `.lab/lab.toml` (profil, version du kit), `work/` avec les templates,
  les recettes `evals` / `evals-collect` du justfile (si absentes), un `.claude/settings.json`
  **fusionné** avec les hooks et denies du kit, le bloc de règles dures dans `CLAUDE.md`
  (+ pointeur `AGENTS.md`), et le workflow CI de gate si le profil l'exige. La commande liste
  chaque fichier créé ou modifié.
- **Edge cases :**
  - **BHV-1a** — `.claude/settings.json` existant avec des hooks utilisateur : fusion, les
    hooks existants sont conservés.
  - **BHV-1b** — Projet non-Python sans evals : la recette `evals` générée échoue fermée
    (« no evals configured »), elle n'est jamais verte par absence.
  - **BHV-1c** — Second lancement : idempotent, « 0 changement ».
  - **BHV-1d** — `--dry-run` : affiche le plan de modifications, n'écrit rien.

### BHV-2 — Les garde-fous voyagent en mode instance externe
- **Given** un run `orchestrate.py <feature> --project <instance>`
- **When** le moteur invoque un agent
- **Then** l'appel embarque les settings du kit (hooks + denies) et les règles dures, même si
  l'instance n'a ni `.claude/` ni `CLAUDE.md`.

### BHV-3 — Profils d'organisation (`lab policy`)
- **Given** `.lab/lab.toml` avec `profile = "<p>"` et une section `[overrides]`
- **When** le FDE lance `lab policy` (ou un run démarre)
- **Then** la politique effective est calculée et affichée clé par clé avec son origine
  (plancher / override). Clés minimales : `max_task_attempts`, `max_parallel`,
  `max_cp_rejects`, `max_tasks_between_checkpoints`, `auto_checkpoints_allowed`,
  `min_reviewers`, `sandbox_required`, `budget_usd`, `plan_lint_blocking_in_ci`, et le mode
  + budget de chaque route d'échec. Les constantes aujourd'hui codées en dur dans
  `orchestrate.py` (`MAX_EVAL_RETRIES`, `MAX_PARALLEL`, `MAX_CP_REJECTS`) en sont lues.
- **Edge cases :**
  - **BHV-3a** — Override plus laxiste que le plancher : refus, rc 1, message nommant la clé,
    la valeur demandée et le plancher.
  - **BHV-3b** — Clé inconnue : erreur (pas de faute de frappe silencieuse).

### BHV-4 — Workflow de bout en bout (`lab next <feature>`)
- **Given** un triplet dans n'importe quel état
- **When** le FDE (ou la CI) lance `lab next <feature>`
- **Then** le moteur déduit la phase courante des `status:` du frontmatter et de
  `.runs/state.json`, évalue son critère de sortie, puis soit lance l'étape agent suivante,
  soit affiche la décision humaine attendue (qui, quoi, commande à lancer). Idempotent.
- Critères de sortie par phase :

  | Phase | `exit_gate` | Décideur |
  |---|---|---|
  | spec | spec-lint : IDs uniques, chaque BHV/INV couvert par un EVAL, 0 OQ ouverte, `status: validated` | Métier |
  | design | design-lint : chaque ADR cite un pattern de référence ou se déclare « sans référence — ADR délibéré » | FDE |
  | plan | plan-lint vert + `status: approved` | Owner |
  | build | verify + evals + anti-empty-gate (existant) | automatique |
  | review | verdict du panel (existant) | auto ou Owner selon le mode du CP |
  | merge | — | Owner, toujours |

### BHV-5 — Routage des échecs (retours arrière)
- **Given** un signal d'échec émis pendant le run
- **When** le moteur le classe
- **Then** il applique la route correspondante de la politique effective. Routes par défaut :

  | Route | Signal | Retour vers | Mode | Budget |
  |---|---|---|---|---|
  | R1 | verify/eval rouge, tentative < max | même tâche, même session, sortie injectée (existant) | auto | `max_task_attempts` |
  | R2 | eval rouge à la dernière tentative | planner → `plan_delta` re-découpant la tâche | proposal | 1 |
  | R3 | `STATUS: blocked — OQ-n` | spec : OQ consignée, tâches impactées listées | human | — |
  | R4 | `STATUS: blocked — ADR` (pattern inapplicable) | design-scout lancé, proposition d'ADR | proposal | 1 |
  | R5 | `STATUS: blocked — scope` (files_touched) | planner → `plan_delta` | proposal | 1 |
  | R6 | panel `BLOCK` sur un CP `auto` | tâches du CP, rapport reviewer injecté comme rework | auto | 1, puis human |
  | R7 | CP rejeté par l'Owner | tâches ciblées + invalidation des dépendants `done` (BHV-6) | auto | `max_cp_rejects` |

- **Edge cases :**
  - **BHV-5a** — Budget de route épuisé : escalade humaine, sous-arbre `skipped`, les autres
    branches continuent (containment existant préservé).
  - **BHV-5b** — Un `plan_delta` approuvé et signé : le run reprend sur le graphe amendé sans
    rejouer les nœuds `done` hors delta.
  - **BHV-5c** — Signal non classable (STATUS sans catégorie) : route `human`, jamais `auto`.

### BHV-6 — Cascade d'invalidation
- **Given** une tâche `done` rouverte (R7)
- **When** elle repasse `pending`
- **Then** ses dépendants transitifs `done` (hors checkpoints) repassent `pending` avec la note
  de rework « amont <Tn> modifié », pour qu'aucun nœud ne reste validé sur une entrée périmée.

### BHV-7 — Boucle d'apprentissage (`lab retro export` / `lab retro report`)
- **Given** un ou plusieurs runs terminés dans une instance
- **When** le FDE lance `lab retro export <feature>`
- **Then** un `retro_record` JSON anonymisé est produit (INV-6) ; dans le kit,
  `lab retro report` agrège tous les records : taux de premier passage par rôle/modèle,
  **taux d'emprunt par route**, interventions humaines par feature, coût par feature —
  ventilés par version du kit et par profil.

## 5. Examples

### EX-1 — Monotonie du plancher
```yaml
input:
  floor: regulated          # min_reviewers = 2, sandbox_required = true
  overrides: {min_reviewers: 1}
expected_output: "rc 1 — min_reviewers=1 is looser than floor 'regulated' (2)"
---
input:
  floor: regulated
  overrides: {min_reviewers: 3}
expected_output: {effective.min_reviewers: 3, origin: override}
covers: [INV-2, BHV-3, BHV-3a]
```

### EX-2 — Route R2 : eval rouge persistante
```yaml
input:
  journal: [eval_fail T4 a1, eval_fail T4 a2, eval_fail T4 a3]
  policy: {max_task_attempts: 3, route.R2.mode: proposal}
expected_output:
  state: {T4: failed, T5: skipped}
  files_created: [.runs/T4-R2-plan-delta.md]
  tasks_md_changed: false          # INV-3
  other_branches: continue
covers: [BHV-5, BHV-5a, INV-3, INV-4]
```

### EX-3 — Route R3 : trou de spec
```yaml
input:
  agent_reply_last_line: "STATUS: blocked — OQ-4 (arrondi TVA par ligne ou par total ?)"
expected_output:
  state: {T2: blocked}
  notification: "T2 blocked on OQ-4 — Owner decision; impacted: [T2, T5, CP-1]"
  spec_md_version: unchanged until human amendment
covers: [BHV-5, INV-3]
```

### EX-4 — Bootstrap idempotent
```yaml
input: {project: empty git repo, command: "lab init . --profile squad"}
expected_output:
  first_run_created: [.lab/lab.toml, work/, .claude/settings.json, CLAUDE.md, AGENTS.md, justfile]
  second_run: "0 changement"
covers: [BHV-1, BHV-1c, INV-7]
```

### EX-5 — Garde-fous en instance externe
```yaml
input: {run: "orchestrate.py work/f --project /tmp/inst", instance_has_claude_dir: false}
expected_output:
  agent_argv_contains: ["--settings", "<kit>/…"]
  agent_write_to: ".approvals/CP-1"
  result: denied
covers: [BHV-2, INV-1]
```

### EX-6 — Retro anonymisé
```yaml
expected_output:
  retro_record:
    kit_version: 0.4.0
    profile: squad
    tasks: 6
    first_pass_rate: 0.67
    routes_taken: {R1: 3, R3: 1}
    human_decisions: 3
    cost_usd: 4.12
    models: {implementer: <model-id>, reviewer: <model-id>}
  forbidden_fields: [feature_name, client, file_paths, spec_text]
covers: [BHV-7, INV-6]
```

## 6. Non-goals

- **NG-1** — Pas d'auto-merge ni d'auto-amendement de spec/design (INV-3, INV-5).
- **NG-2** — Pas de dépendance runtime à un framework d'orchestration (LangGraph, Airflow…) :
  on emprunte le pattern (arêtes conditionnelles déclaratives, interruption humaine), le
  moteur reste stdlib.
- **NG-3** — Pas de serveur de télémétrie central : les retros sont des fichiers versionnés
  (le repo est la mémoire).
- **NG-4** — Pas de runner multi-vendor dans cette feature (backlog existant).
- **NG-5** — Pas de modification automatique des agents `.md` ou du registry à partir des
  retros : la boucle `lab/models/EVOLUTION.md` reste validée par un humain.

## 7. Evals — merge gate

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | `lab init` sur repo vide crée exactement les fichiers d'EX-4 ; 2ᵉ run = 0 diff ; settings existants fusionnés ; recette evals non-Python échoue fermée | BHV-1, BHV-1a, BHV-1b, BHV-1c, BHV-1d, INV-7 | 100% |
| EVAL-2 | deterministic | en `--project`, l'argv agent (shim) porte les settings du kit ; écriture `.approvals/` refusée | BHV-2, INV-1 | 100% |
| EVAL-3 | deterministic | EX-1 ; clé inconnue rejetée ; les constantes du moteur proviennent de la politique effective | BHV-3, BHV-3a, BHV-3b, INV-2, INV-5 | 100% |
| EVAL-4 | deterministic | `lab next` sur 6 triplets fixtures (un par phase) annonce la bonne phase et la bonne action ; idempotent | BHV-4 | 100% |
| EVAL-5 | deterministic | shim rejouant R1–R7 : bonne cible, bon mode, budgets respectés, aucun artefact humain modifié | BHV-5, BHV-5a, BHV-5b, BHV-5c, INV-3, INV-4 | 100% |
| EVAL-6 | deterministic | réouverture de T1 remet en `pending` ses dépendants `done` | BHV-6 | 100% |
| EVAL-7 | deterministic | `retro export` ne contient aucun champ interdit et passe `brand_guard` ; `retro report` agrège EX-6 exactement | BHV-7, INV-6 | 100% |

## 8. Open questions

- **OQ-1** — Distribution de la partie `.claude/` (agents, skills, hooks) : plugin Claude Code
  installé côté FDE (voyage avec lui, le repo client reste propre), copie dans l'instance par
  `lab init` (l'équipe client en hérite), ou **hybride** — agents/skills en plugin, hooks +
  denies copiés dans l'instance parce qu'ils doivent s'appliquer à quiconque travaille sur le repo ?
- **OQ-2** — Séparation kit / produit : ce repo devient le kit et `src/devis`, `src/booking`,
  leurs `work/` et `tests/` migrent sous `examples/` (déjà anticipé par `.githooks/pre-commit`),
  ou le kit part dans un repo dédié ?
- **OQ-3** — Profils livrés et leurs valeurs : `solo` (FDE seul, POC), `squad` (FDE + équipe
  client, défaut), `regulated` (sandbox obligatoire, tous les CP bloquants, panel ≥ 2) ?
- **OQ-4** — Un profil `solo` peut-il auto-approuver un `plan_delta` qui lint vert et ne touche
  que des nœuds non démarrés (R2/R5 en mode `auto`), ou la proposition reste-t-elle toujours humaine ?
- **OQ-5** — Où l'implementer consigne-t-il une OQ : dans `spec.md` §8 (comportement actuel —
  modifie la substance sans bump, en tension avec INV-3) ou dans une proposition `.runs/OQ-n.md`
  que l'Owner reporte dans la spec en l'amendant ?
- **OQ-6** — Cascade d'invalidation (BHV-6) : reset systématique des dépendants `done`, ou
  seulement de ceux dont les `files_touched`/IDs recoupent ceux de la tâche rouverte ?
- **OQ-7** — Canal de remontée des retros vers le kit (commit sous `lab/retro/` du kit, PR,
  dépôt manuel) et niveau d'anonymisation acceptable contractuellement pour les clients ?
- **OQ-8** — Baseline du KPI « interventions humaines hors checkpoints » : mesurer sur les
  prochains runs avant de fixer une cible chiffrée ?

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-11-12 | Owner + agent | Brouillon issu de l'audit du workflow existant (ce qui marche, trous vérifiés) — à itérer sur les OQ |
