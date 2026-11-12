---
type: spec
feature: fde-kit
version: 0.2.0
status: draft            # draft | validated | superseded
owner: Antoine (Owner)
validated_by:            # vide tant que draft — OQ-1..8 tranchées le 2026-11-12, validation Owner attendue
---

# Spec — Kit FDE portable : workflow agentique templatisé, profils d'organisation, retours arrière routés

## 1. Intent

Un FDE arrive sur une nouvelle mission **avec son propre outillage** : son SDLC agentique
(moteur, agents, skills, garde-fous) l'accompagne sous forme de **plugin personnel**, et
s'active dans le projet client en quelques minutes, au **niveau de contrôle adapté à
l'organisation** (FDE seul sur un POC, squad mixte, environnement régulé), sans réécrire le
workflow ni déposer d'outillage dans le repo client. Une fois le plan approuvé, le workflow
**enchaîne les phases seul** entre deux décisions humaines et, quand un agent n'atteint pas
son objectif, **renvoie l'échec vers l'artefact responsable** (code → plan → design → spec)
sous forme de proposition, au lieu de simplement réessayer ou de s'arrêter. Chaque mission
**rend le kit meilleur** : ses retours anonymisés restent chez le FDE et alimentent sa boucle
d'évolution.

**Target KPI :**
- Bootstrap d'un projet vierge jusqu'au premier `lab next` vert : non mesuré aujourd'hui
  (copie manuelle des templates + `--project`) → **≤ 30 min**.
- Garde-fous du kit actifs dans un run orchestré sur une instance externe : **0 garanti
  aujourd'hui** (aucun `--settings` transmis en mode `--project`) → **100 %** (INV-1).
- Interventions humaines hors checkpoints prévus, par feature : **baseline mesurée sur les
  3 prochaines features**, cible chiffrée fixée ensuite par amendement (OQ-8).

## 2. Glossary

| Business term | Canonical name (code) | Definition |
|---|---|---|
| Kit | `kit` | L'outillage versionné du FDE : moteur (`lab/engine`), agents, skills, hooks, règles dures, templates, registry, profils. Ce repo. |
| Plugin FDE | `fde_plugin` | Distribution du kit côté agent (agents, skills, hooks, denies, règles dures), installée chez le FDE ; seul canal de distribution en 0.x |
| Instance | `instance` | Un projet client activé par le kit : `work/`, code, evals, `.lab/lab.toml` — aucun outillage agent |
| Profil d'organisation | `policy_profile` | Jeu nommé de réglages : `solo`, `squad`, `regulated` |
| Plancher | `policy_floor` | Profil choisi pour l'instance ; une instance peut le durcir, jamais l'assouplir |
| Clé de sécurité | `safety_key` | Clé de profil avec une direction « plus strict » déclarée, soumise au plancher |
| Clé libre | `free_key` | Clé de profil sans direction de sécurité (performance, coût) ; override libre |
| Politique effective | `effective_policy` | Résultat de la fusion plancher ⊕ overrides de l'instance, clé par clé |
| Phase | `phase` | Étape du SDLC : `spec` → `design` → `plan` → `build` → `review` → `merge` |
| Critère de sortie | `exit_gate` | Check mécanique qui conditionne la transition vers la phase suivante |
| Signal d'échec | `failure_signal` | Événement classé émis quand un agent n'atteint pas son objectif (eval rouge, STATUS blocked, verdict BLOCK…) |
| Route d'échec | `failure_route` | Règle déclarative : signal → phase cible → mode (`auto` / `proposal` / `human`) → budget de boucles |
| Retour arrière | `backtrack` | Transition vers une phase amont déclenchée par une route d'échec |
| Delta de plan | `plan_delta` | Diff de `tasks.md` limité aux nœuds non démarrés, soumis à une approbation humaine signée |
| Retro | `retro_record` | Résumé anonymisé d'un run (compteurs, durées, coûts, modèles, routes empruntées), stocké chez le FDE |

## 3. Invariants

- **INV-1** — Les garde-fous du kit (denies `.approvals/` et `.runs/`, eval gate `Stop`/`SubagentStop`,
  règles dures, approbations signées fail-closed) MUST être actifs à l'identique dans tout run
  orchestré, que le run s'exécute dans le repo du kit ou dans une instance externe — y compris
  une instance sans `.claude/` ni `CLAUDE.md`.
- **INV-2** — Une instance MUST NOT assouplir une clé de sécurité sous son plancher : pour chaque
  `safety_key`, `effective_policy` = la valeur la plus stricte entre plancher et override.
- **INV-3** — Un retour arrière MUST NOT modifier un artefact humain (`spec.md`, `design.md`, un
  `tasks.md` au statut `approved`) : il produit une **proposition** (`.runs/<id>-<route>.md` +
  notification), appliquée seulement après décision humaine signée — **quel que soit le profil**.
  Aucune clé de profil ne peut passer les routes R2, R3, R4, R5 en mode `auto`.
- **INV-4** — Chaque route d'échec a un budget de boucles fini ; budget épuisé ⇒ escalade humaine.
  Aucun cycle de retour arrière ne peut boucler indéfiniment.
- **INV-5** — Le merge reste humain dans **tous** les profils ; aucune clé de profil ne peut le
  rendre `auto`.
- **INV-6** — Un `retro_record` MUST NOT contenir de nom propre client/brand, de chemin d'asset ni
  de contenu de spec : uniquement des IDs, compteurs, durées, coûts, modèles, versions, noms de
  routes. Il passe `brand_guard`.
- **INV-7** — Une instance épingle la version du kit (`.lab/lab.toml`) ; tout upgrade du kit est
  un commit explicite de l'instance, jamais une dérive silencieuse.
- **INV-8** — `lab init` MUST NOT écrire d'outillage agent dans l'instance (rien sous `.claude/`, ni
  agents, ni skills, ni hooks, ni règles dures, ni `CLAUDE.md`/`AGENTS.md`) : l'instance ne reçoit
  que des données projet (`.lab/lab.toml`, `work/`, recettes d'evals du justfile).
- **INV-9** — Le kit ne package que le moteur : le code produit de démonstration (`devis`,
  `booking`) et ses triplets/tests vivent sous `examples/`.
- **INV-10** — Pendant un run, aucun agent ne modifie `spec.md` ni `design.md` : une tâche dont le
  working tree touche l'un d'eux échoue, et le commit scopé ne les stage jamais.
- **INV-11** — Un `retro_record` n'est jamais écrit dans un repo (ni l'instance, ni le kit) : il vit
  dans le stockage local du FDE.

## 4. Behaviors

### BHV-1 — Activation d'une instance (`lab init <project> --profile <p>`)
- **Given** un repo git sans le kit, et le plugin FDE installé chez le FDE
- **When** le FDE lance `lab init <project> --profile squad`
- **Then** sont créés : `.lab/lab.toml` (profil, version du kit épinglée), `work/` avec les
  templates du triplet, et les recettes `evals` / `evals-collect` du justfile si elles sont
  absentes. Rien d'autre (INV-8). La commande liste chaque fichier créé ou modifié.
- **Edge cases :**
  - **BHV-1a** — *(retiré en 0.2.0 — plus de `.claude/settings.json` écrit dans l'instance, OQ-1)*
  - **BHV-1b** — Projet non-Python sans evals : la recette `evals` générée échoue fermée
    (« no evals configured »), elle n'est jamais verte par absence.
  - **BHV-1c** — Second lancement : idempotent, « 0 changement ».
  - **BHV-1d** — `--dry-run` : affiche le plan de modifications, n'écrit rien.
  - **BHV-1e** — Justfile existant avec une recette `evals` : conservée telle quelle, jamais écrasée.

### BHV-2 — Les garde-fous voyagent avec le plugin
- **Given** un run `orchestrate.py <feature> --project <instance>`
- **When** le moteur invoque un agent
- **Then** l'appel embarque les settings du kit (hooks + denies) et les règles dures, même si
  l'instance n'a ni `.claude/` ni `CLAUDE.md`.
- **Edge cases :**
  - **BHV-2a** — Plugin FDE absent, ou de version ≠ celle épinglée dans `.lab/lab.toml` : le run
    refuse de démarrer (rc 1, message nommant les deux versions). Fail-closed.
  - **BHV-2b** — Session interactive ouverte dans l'instance avec le plugin activé : les règles
    dures sont présentes dans le contexte de la session sans aucun fichier de règles dans l'instance.

### BHV-3 — Profils d'organisation (`lab policy`)
- **Given** `.lab/lab.toml` avec `profile = "<p>"` et une section `[overrides]`
- **When** le FDE lance `lab policy` (ou un run démarre)
- **Then** la politique effective est calculée et affichée clé par clé avec son origine
  (plancher / override). Les constantes aujourd'hui codées en dur dans `orchestrate.py`
  (`MAX_EVAL_RETRIES`, `MAX_PARALLEL`, `MAX_CP_REJECTS`) en sont lues. Profils livrés :

  | Clé | Type · direction stricte | solo | squad | regulated | Appliquée par |
  |---|---|---|---|---|---|
  | `auto_checkpoints_allowed` | sécurité · `false` | true | true | false | plan-lint (erreur sur `mode: auto`) |
  | `min_reviewers` | sécurité · ↑ | 1 | 1 | 2 | plan-lint (`reviewers` d'un CP < min) |
  | `max_tasks_between_checkpoints` | sécurité · ↓ | 8 | 5 | 3 | plan-lint |
  | `sandbox_required` | sécurité · `true` | false | false | true | démarrage du run (`LAB_RUNNER=sandbox` exigé) |
  | `allow_force` | sécurité · `false` | true | true | false | démarrage du run (`--force` refusé) |
  | `max_task_attempts` | libre | 3 | 3 | 3 | moteur (route R1) |
  | `max_parallel` | libre | 3 | 3 | 2 | moteur |
  | `max_cp_rejects` | libre | 2 | 2 | 2 | moteur (route R7) |
  | `budget_usd` | libre · 0 = sans plafond | 0 | 0 | 0 | moteur |

- **Edge cases :**
  - **BHV-3a** — Override d'une clé de sécurité plus laxiste que le plancher : refus, rc 1,
    message nommant la clé, la valeur demandée et le plancher.
  - **BHV-3b** — Clé inconnue : erreur (pas de faute de frappe silencieuse).
  - **BHV-3c** — Override tentant de passer une route R2/R3/R4/R5 en `auto` : refus, rc 1 (INV-3).

### BHV-4 — Workflow de bout en bout (`lab next <feature>`)
- **Given** un triplet dans n'importe quel état
- **When** le FDE lance `lab next <feature>`
- **Then** le moteur déduit la phase courante des `status:` du frontmatter et de
  `.runs/state.json`, évalue son critère de sortie, puis soit lance l'étape agent suivante,
  soit affiche la décision humaine attendue (qui, quoi, commande à lancer). Idempotent.
- Critères de sortie par phase :

  | Phase | `exit_gate` | Décideur |
  |---|---|---|
  | spec | spec-lint : IDs uniques, chaque BHV/INV couvert par un EVAL, 0 OQ ouverte, `status: validated` | Métier |
  | design | design-lint : chaque ADR cite un pattern de référence ou se déclare « sans référence — ADR délibéré » | FDE |
  | plan | plan-lint vert (avec la politique effective) + `status: approved` | Owner |
  | build | verify + evals + anti-empty-gate (existant) | automatique |
  | review | verdict du panel (existant) | auto ou Owner selon le mode du CP |
  | merge | — | Owner, toujours |

### BHV-5 — Routage des échecs (retours arrière)
- **Given** un signal d'échec émis pendant le run
- **When** le moteur le classe
- **Then** il applique la route correspondante de la politique effective :

  | Route | Signal | Retour vers | Mode | Budget |
  |---|---|---|---|---|
  | R1 | verify/eval rouge, tentative < max | même tâche, même session, sortie injectée (existant) | auto | `max_task_attempts` |
  | R2 | eval rouge à la dernière tentative | planner → `plan_delta` re-découpant la tâche | proposal (humain, tous profils) | 1 |
  | R3 | `STATUS: blocked — OQ` | l'agent formule l'OQ dans sa réponse ; le **moteur** l'écrit dans `.runs/<Tn>-OQ.md` ; l'Owner l'intègre par amendement versionné | human | — |
  | R4 | `STATUS: blocked — ADR` (pattern inapplicable) | design-scout lancé, proposition d'ADR | proposal (humain, tous profils) | 1 |
  | R5 | `STATUS: blocked — scope` (files_touched) | planner → `plan_delta` | proposal (humain, tous profils) | 1 |
  | R6 | panel `BLOCK` sur un CP `auto` | tâches du CP, rapport reviewer injecté comme rework | auto | 1, puis human |
  | R7 | CP rejeté par l'Owner | tâches ciblées + reset ciblé des dépendants (BHV-6) | auto | `max_cp_rejects` |

- **Edge cases :**
  - **BHV-5a** — Budget de route épuisé : escalade humaine, sous-arbre `skipped`, les autres
    branches continuent (containment existant préservé).
  - **BHV-5b** — Un `plan_delta` approuvé et signé : le run reprend sur le graphe amendé sans
    rejouer les nœuds `done` hors delta.
  - **BHV-5c** — Signal non classable (STATUS sans catégorie) : route `human`, jamais `auto`.

### BHV-6 — Reset ciblé des dépendants
- **Given** une tâche `done` rouverte (R7)
- **When** elle repasse `pending`
- **Then** parmi ses dépendants transitifs `done` (hors checkpoints), seuls ceux dont les
  `files_touched` recoupent les siens **ou** qui partagent un ID de spec implémenté repassent
  `pending`, avec la note de rework « amont <Tn> modifié ».
- **Edge cases :**
  - **BHV-6a** — Dépendant sans recoupement : reste `done`, mais est listé dans la notification
    (« non relancé : aucun recoupement »).
  - **BHV-6b** — Filet de sécurité : l'eval globale du checkpoint suivant couvre les dépendants
    non relancés ; une eval rouge à ce checkpoint déclenche R6/R7.

### BHV-7 — Boucle d'apprentissage locale (`lab retro export` / `lab retro report`)
- **Given** un ou plusieurs runs terminés dans une instance
- **When** le FDE lance `lab retro export <feature>`
- **Then** un `retro_record` JSON anonymisé (INV-6) est écrit dans le stockage local du FDE, hors
  de tout repo (INV-11) ; `lab retro report` agrège tous les records locaux : taux de premier
  passage par rôle/modèle, **taux d'emprunt par route**, **interventions humaines hors
  checkpoints prévus** (KPI), coût par feature — ventilés par version du kit et par profil.
  Seul le rapport agrégé peut être partagé, manuellement, par le FDE.

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
  overrides: {min_reviewers: 3, max_parallel: 4}
expected_output:
  effective: {min_reviewers: 3, max_parallel: 4}
  origin: {min_reviewers: override, max_parallel: override (free key)}
covers: [INV-2, BHV-3, BHV-3a]
```

### EX-2 — Route R2 : eval rouge persistante
```yaml
input:
  journal: [eval_fail T4 a1, eval_fail T4 a2, eval_fail T4 a3]
  policy: {profile: solo, max_task_attempts: 3}
expected_output:
  state: {T4: failed, T5: skipped}
  files_created: [.runs/T4-R2-plan-delta.md]
  tasks_md_changed: false          # INV-3, même en solo
  awaiting: signed human approval of the delta
  other_branches: continue
covers: [BHV-5, BHV-5a, INV-3, INV-4]
```

### EX-3 — Route R3 : trou de spec
```yaml
input:
  agent_reply_tail: |
    OQ: arrondi TVA par ligne ou par total ?
    STATUS: blocked — OQ
expected_output:
  state: {T2: blocked}
  files_created: [.runs/T2-OQ.md]       # écrit par le moteur, pas par l'agent
  spec_md: byte-identical               # INV-10
  notification: "T2 blocked on an open question — Owner amendment expected; impacted: [T2, T5, CP-1]"
covers: [BHV-5, INV-3, INV-10]
```

### EX-4 — Activation idempotente, sans outillage dans l'instance
```yaml
input: {project: empty git repo, command: "lab init . --profile squad"}
expected_output:
  first_run_created: [.lab/lab.toml, work/, justfile]
  never_created: [.claude/, CLAUDE.md, AGENTS.md]
  second_run: "0 changement"
covers: [BHV-1, BHV-1c, INV-7, INV-8]
```

### EX-5 — Garde-fous en instance externe
```yaml
input: {run: "orchestrate.py work/f --project /tmp/inst", instance_has_claude_dir: false}
expected_output:
  agent_argv_contains: ["--settings", "<kit>/…"]
  agent_write_to: ".approvals/CP-1"
  result: denied
---
input: {plugin_version: 0.3.0, pinned_kit_version: 0.4.0}
expected_output: "rc 1 — plugin 0.3.0 ≠ pinned kit 0.4.0"
covers: [BHV-2, BHV-2a, INV-1]
```

### EX-6 — Retro anonymisé et local
```yaml
expected_output:
  written_to: "<stockage local FDE>/retro/<date>-<hash>.json"   # hors de tout repo
  retro_record:
    kit_version: 0.4.0
    profile: squad
    tasks: 6
    first_pass_rate: 0.67
    routes_taken: {R1: 3, R3: 1}
    human_interventions_unplanned: 1
    cost_usd: 4.12
    models: {implementer: <model-id>, reviewer: <model-id>}
  forbidden_fields: [feature_name, client, file_paths, spec_text]
covers: [BHV-7, INV-6, INV-11]
```

### EX-7 — Reset ciblé
```yaml
input:
  reopened: T1        # files_touched: [src/calc/], implements: [BHV-1]
  done_dependents:
    T3: {files_touched: [src/calc/rounding.py], implements: [BHV-2]}
    T4: {files_touched: [src/cli/], implements: [BHV-1]}
    T5: {files_touched: [docs/usage.md], implements: [BHV-4]}
expected_output:
  pending: [T1, T3, T4]           # T3 recoupe par fichier, T4 par ID
  stays_done: [T5]
  notification_lists: "T5 non relancé : aucun recoupement"
covers: [BHV-6, BHV-6a]
```

## 6. Non-goals

- **NG-1** — Pas d'auto-merge ni d'auto-amendement de spec/design (INV-3, INV-5).
- **NG-2** — Pas de dépendance runtime à un framework d'orchestration (LangGraph, Airflow…) :
  on emprunte le pattern (arêtes conditionnelles déclaratives, interruption humaine), le
  moteur reste stdlib.
- **NG-3** — Pas de serveur de télémétrie central ni de remontée des retros dans le repo du kit
  (OQ-7) : les records restent chez le FDE.
- **NG-4** — Pas de runner multi-vendor dans cette feature (backlog existant).
- **NG-5** — Pas de modification automatique des agents `.md` ou du registry à partir des
  retros : la boucle `lab/models/EVOLUTION.md` reste validée par un humain.
- **NG-6** — Pas de « mode instance » en 0.x (hooks, settings, règles et workflow CI copiés dans
  le repo client pour que l'équipe client en hérite) : second mode prévu une fois le modèle
  plugin éprouvé (OQ-1). Limite acceptée d'ici là : une session lancée sans le plugin n'a pas
  les garde-fous du kit.

## 7. Evals — merge gate

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | `lab init` sur repo vide crée exactement les fichiers d'EX-4, aucun fichier d'outillage ; 2ᵉ run = 0 diff ; recette `evals` existante préservée ; recette non-Python échoue fermée ; `--dry-run` n'écrit rien | BHV-1, BHV-1b, BHV-1c, BHV-1d, BHV-1e, INV-7, INV-8 | 100% |
| EVAL-2 | deterministic | en `--project`, l'argv agent (shim) porte les settings du kit ; écriture `.approvals/` refusée ; plugin absent ou version ≠ pin ⇒ rc 1 ; règles dures présentes en session interactive | BHV-2, BHV-2a, BHV-2b, INV-1 | 100% |
| EVAL-3 | deterministic | EX-1 ; table des profils exacte ; chaque clé de sécurité appliquée mécaniquement (plan-lint, refus `--force`, sandbox exigé) ; clé inconnue rejetée ; R2–R5 non passables en `auto` ; constantes du moteur lues depuis la politique effective | BHV-3, BHV-3a, BHV-3b, BHV-3c, INV-2, INV-3, INV-5 | 100% |
| EVAL-4 | deterministic | `lab next` sur 6 triplets fixtures (un par phase) annonce la bonne phase et la bonne action ; idempotent | BHV-4 | 100% |
| EVAL-5 | deterministic | shim rejouant R1–R7 : bonne cible, bon mode, budgets respectés, propositions écrites par le moteur, aucun artefact humain modifié | BHV-5, BHV-5a, BHV-5b, BHV-5c, INV-3, INV-4 | 100% |
| EVAL-6 | deterministic | EX-7 exact ; eval globale du CP suivant exécutée | BHV-6, BHV-6a, BHV-6b | 100% |
| EVAL-7 | deterministic | `retro export` écrit hors de tout repo, sans champ interdit, passe `brand_guard` ; `retro report` agrège EX-6 exactement, KPI inclus | BHV-7, INV-6, INV-11 | 100% |
| EVAL-8 | deterministic | le package du kit n'embarque que le moteur ; `devis` et `booking` (code, triplets, tests) sous `examples/` ; `just gate-ci` vert après migration | INV-9 | 100% |
| EVAL-9 | deterministic | une tâche (shim) qui modifie `spec.md` ou `design.md` échoue ; le commit scopé ne stage jamais spec/design | INV-10 | 100% |

## 8. Open questions

- **OQ-1** — Distribution de la partie agent du kit → *(résolue le 2026-11-12 : tout en plugin FDE ;
  un second mode « instance » est prévu une fois le modèle éprouvé — intégré en INV-8, BHV-2a,
  BHV-2b, NG-6 ; BHV-1a retiré)*
- **OQ-2** — Séparation kit / produit → *(résolue le 2026-11-12 : ce repo devient le kit, `devis` et
  `booking` migrent sous `examples/` — intégré en INV-9, EVAL-8)*
- **OQ-3** — Profils livrés → *(résolue le 2026-11-12 : `solo` / `squad` / `regulated` — intégré en
  BHV-3, table des profils)*
- **OQ-4** — Approbation d'un `plan_delta` → *(résolue le 2026-11-12 : toujours humaine, dans tous
  les profils — intégré en INV-3, BHV-3c)*
- **OQ-5** — Où consigner une OQ levée par un agent → *(résolue le 2026-11-12 : proposition dans
  `.runs/`, écrite par le moteur depuis la réponse de l'agent — `.runs/` reste interdit en écriture
  aux agents ; intégré en INV-10, route R3)*
- **OQ-6** — Cascade d'invalidation → *(résolue le 2026-11-12 : reset ciblé par recoupement de
  fichiers ou d'IDs — intégré en BHV-6)*
- **OQ-7** — Remontée des retros → *(résolue le 2026-11-12 : restent locales au FDE — intégré en
  INV-11, BHV-7, NG-3)*
- **OQ-8** — Cible du KPI interventions humaines → *(résolue le 2026-11-12 : mesurer une baseline
  sur 3 features, puis amender — intégré en §1)*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-11-12 | Owner + agent | Brouillon issu de l'audit du workflow existant (ce qui marche, trous vérifiés) — à itérer sur les OQ |
| 0.2.0 | 2026-11-12 | Owner | OQ-1..8 tranchées par QCM : distribution 100 % plugin, ce repo = kit, profils solo/squad/regulated avec clés de sécurité vs libres, plan_delta toujours humain, OQ agent → `.runs/` via le moteur, reset ciblé, retros locales, KPI mesuré d'abord. Ajouts INV-8..11, BHV-1e, BHV-2a/b, BHV-3c, BHV-6a/b, EX-7, EVAL-8/9, NG-6 ; BHV-1a retiré |
