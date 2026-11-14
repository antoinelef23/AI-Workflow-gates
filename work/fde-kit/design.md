---
type: design
feature: fde-kit
version: 0.7.1
status: draft            # draft | validated | superseded
owner: Antoine (Owner)
validated_by: FDE — 2026-11-12 (validé en session par QCM ; plugin sous lab/plugin/ confirmé) ; amendement 0.3.0 (OQ-9..11 du planner) approuvé le 2026-11-12 ; amendement 0.4.0 (spike promptfoo) approuvé le 2026-11-12 ; amendement 0.5.0 (itération 2 : profils, sandbox d'instance, kit-instance — 3 décisions Owner par QCM) approuvé le 2026-11-12 ; amendement 0.6.0 (INV-5 garanti aussi à l'exécution, revue CP-7) approuvé le 2026-11-13 ; amendements 0.7.0 et 0.7.1 (itération 3) : **brouillon, en attente de validation Owner**
spec: ./spec.md          # version : 0.9.0
---

# Design — Kit FDE portable

> **Périmètre de cette version : itérations 1 « kit portable » (livrée, `v0.1.0`), 2 « profils
> d'organisation » (livrée, kit 0.2.0) et 3 « workflow de bout en bout » (amendement 0.7.0,
> brouillon)** — itération 1 : BHV-1 (+1b..1e), BHV-2 (+2a, 2b), INV-1, INV-7, INV-8, INV-9,
> EVAL-1, EVAL-2, EVAL-8 ; itération 2 : BHV-3 (+3a..3c), INV-2, INV-3 (volet profils), INV-5,
> EX-1, EVAL-3 (ADR-13..16, ADR-10 remplacé par ADR-15) ; itération 3 : BHV-4, BHV-5 (+5a..5c),
> BHV-6 (+6a, 6b), BHV-8 (+8a..8e), INV-3 (volet routes), INV-4, INV-10, INV-12, EX-2, EX-3, EX-7,
> EX-8, EVAL-4, EVAL-5, EVAL-6, EVAL-9, EVAL-10 (ADR-17..24). L'itération 4 (retro, improver :
> BHV-7, BHV-12) sera conçue à son tour, par amendement de ce document.
>
> Source : rapport `design-scout` du 2026-11-12 (références vérifiées dans la doc officielle,
> le code source de Copier/Black et des essais locaux) + 4 décisions Owner prises par QCM.
> Amendement 0.7.0 : rapport `work/fde-kit/.runs/design-scout-iteration-3.md` (patterns I-26..I-45,
> références E-18..E-20 vérifiées sur page primaire le 2026-11-14) + 6 décisions Owner prises par
> QCM le 2026-11-14 (section « Décisions Owner » du rapport). Amendement 0.7.1 : les 3 points
> restés ouverts (§10) tranchés par l'Owner par QCM le 2026-11-14, sur pièces (section
> « Vérifications » du rapport : scan des blocs EX, smokes d'isolement).

## 1. Architecture overview

Le kit devient **un seul paquet Python** (`fde-kit`) qui embarque le moteur et le plugin
Claude Code, avec **une seule version**. Le FDE l'installe chez lui (`uv tool install`) et
installe le même plugin pour ses sessions interactives (marketplace = ce repo). Une instance
client ne reçoit que des données projet. Dans un run orchestré, **le moteur fournit
explicitement** à chaque appel agent le plugin, les interdictions et les règles dures : aucun
garde-fou de run ne dépend de ce que l'instance ou la machine contiennent par ailleurs.

```mermaid
flowchart LR
    subgraph FDE["Machine du FDE"]
        PKG["fde-kit (uv tool)<br/>lab/engine + lab/plugin<br/>version X"]
        INT["claude interactif<br/>+ plugin fde-kit@X<br/>(marketplace = repo kit)"]
    end
    subgraph INST["Instance client (repo git)"]
        TOML[".lab/lab.toml<br/>kit_version = X, profile"]
        WORK["work/&lt;feature&gt;/ triplet"]
        JF["justfile : evals, evals-collect"]
        CODE["code + evals du client"]
    end
    PKG -- "lab init" --> TOML & WORK & JF
    PKG -- "lab run --project<br/>pré-vol : version X = pin ?" --> RUN["claude -p<br/>--plugin-dir lab/plugin<br/>--settings run_settings.json<br/>--append-system-prompt règles"]
    RUN -- "cwd" --> CODE
    INT -. "SessionStart : règles<br/>PreToolUse : garde chemins<br/>Stop : eval gate" .-> CODE
```

Flux d'un run : pré-vol (racine du kit, version CLI, version épinglée, combinaison
runner/instance) → verrou → boucle DAG existante, inchangée → chaque appel agent passe par
l'unique constructeur `claude_argv`, qui ajoute plugin + settings + règles.

**Itération 3 (amendement 0.7.0).** `lab next <feature>` lit l'état de run (ADR-18), déduit la
phase courante, évalue son critère de sortie et, selon le cas, lance l'étape agent suivante ou
affiche la décision humaine attendue (ADR-17). En phase build, la boucle DAG reste le cœur ; chaque
signal d'échec passe par **un seul classifieur** (ADR-20), qui choisit une route R1..R7 de la
politique effective. Les routes `proposal` et `human` n'écrivent que dans `.runs/` — le moteur,
jamais l'agent — et attendent une décision signée (ADR-21, ADR-22) ; R7 rouvre des tâches avec un
reset ciblé (ADR-23). Le test goldfish (ADR-24) est une commande en lecture seule, branchée dans le
critère de sortie de la phase spec.

```mermaid
flowchart TD
    SIG["signal d'échec<br/>verify/eval rouge · STATUS: blocked<br/>verdict BLOCK · rejet de CP"] --> CL{"classifieur unique<br/>(ADR-20)"}
    CL -- "R1 : tentative &lt; max" --> RETRY["même tâche, même session"]
    CL -- "R2 / R4 / R5" --> PROP[".runs/&lt;id&gt;-&lt;route&gt;.md<br/>écrit par le moteur"]
    CL -- "R3" --> OQ[".runs/&lt;Tn&gt;-OQ.md<br/>écrit par le moteur"]
    CL -- "R6 : BLOCK sur CP auto" --> RW["rework des tâches du CP"]
    CL -- "R7 : rejet signé" --> RESET["reset ciblé (ADR-23)"]
    CL -- "non classable · budget épuisé" --> HUM["escalade humaine<br/>sous-arbre skipped"]
    PROP --> SIGN{"décision signée<br/>approve.sh / reject.sh"}
    SIGN -- "approuvée" --> APPLY["appliquée par le moteur,<br/>reprise sur le graphe amendé"]
```

## 2. Reference repositories — the foundation

### 2.1 Internal reference repos

| Repo | Team / contact | Access on day 1? | What we reuse | What we drop |
|---|---|---|---|---|
| ce repo (le kit lui-même) | FDE / Owner | ☑ | patterns I-1..I-45 ci-dessous | anti-patterns de la colonne « à ne pas reproduire » |

| # | Problème | Pattern interne (fichier:ligne) | Réutilisation | À ne pas reproduire |
|---|---|---|---|---|
| I-1 | Settings dans l'argv agent | `lab/engine/runner.py:48-84` `claude_argv`, constructeur unique hôte + sandbox ; ajouts conditionnels `:78-79` | Ajouter plugin/settings/règles ici, une seule fois ; argv inchangé quand non demandé (`tests/orchestrator/test_external_project.py:64-80`) | `lab/engine/eval_models.py:83-99` construit son propre argv (corrigé par ADR-11) |
| I-2 | Racine kit vs racine build | `orchestrate.py:81-95`, `:217`, `:748-757` | Plugin et settings résolus depuis LAB, jamais depuis PROJECT | Porter de la config via `--add-dir` (ne charge ni hooks ni denies) |
| I-3 | Interdictions | `.claude/settings.json:6-17` | `Edit(**/.approvals/**)`, `Edit(**/.runs/**)` (ancrés au cwd, corrects via `--settings`) | Entrées `Write`/`MultiEdit`/`NotebookEdit` : acceptées mais jamais appliquées |
| I-4 | Eval gate de session | `.claude/hooks/eval_gate.sh:11-12` (garde de boucle), `:25-31` (exit 2) | Devient un hook du plugin, appelé via `${CLAUDE_PLUGIN_ROOT}` | Chemins `$CLAUDE_PROJECT_DIR/.claude/hooks/…` (introuvables en instance ⇒ exit 127 non bloquant) ; `:15` sort en 0 sans `pyproject.toml` |
| I-5 | Refus de démarrer | `orchestrate.py:797-808` (pré-vol, rc 1 avant le verrou) | Même forme pour version, runner, racine | — |
| I-6 | Données TOML versionnées | `lab/models/registry.toml:11`, `lab/engine/registry.py:50-63` | `.lab/lab.toml` : `tomllib` + `schema_version` | `registry.py:55-56` : fichier absent ⇒ registre vide silencieux |
| I-7 | Forme CLI / rapport | `lab/engine/brand_guard.py:138-183`, `:53-56` | `lab init` : plan calculé d'abord, une ligne par fichier, rc 0/1 ; variable d'env comme seam de test | — |
| I-8 | Recette présente ? | `orchestrate.py:245-256` `_just_has_recipe` | Idée reprise via `just --justfile <p> --dump --dump-format json` | `just --summary` remonte aux justfiles parents ; échec de parse ⇒ faux négatif ⇒ doublon |
| I-9 | Contrat des recettes d'evals | `orchestrate.py:259-289` | Noms `evals` / `evals-collect` déjà consommés par le moteur | Recette du kit `justfile:72-74` verte sans evals : jamais comme modèle non-Python |
| I-10 | Tests de hooks | `tests/orchestrator/test_hooks.py:17-42` | Tester SessionStart (stdout) et la garde PreToolUse (exit 2) sans session live | — |
| I-11 | Shim agent | `tests/orchestrator/conftest.py:26-42`, `:131-133` (`argv.log`) | Assertions EX-5 sur l'argv | `conftest.py:29` suppose `claude -p` : ajouter une branche `--version` |
| I-12 | Source unique des règles | `work/sdlc-rework/design.md` ADR-5, `tests/sdlc_rework/test_agents_md.py:13-21` | Un seul fichier de règles, lu par le hook et par le moteur | Texte de règles copié dans des chaînes de hook ou en double dans CLAUDE.md |
| I-13 | Tests subprocess | `tests/orchestrator/test_external_project.py:28-42`, `:83-102` | `lab init` sur un repo git temporaire, assertion du jeu de fichiers EX-4 | — |
| I-14 | Imports depuis n'importe où | `lab/engine/eval_models.py:44` | Shim de point d'entrée gardant les imports plats `orchestrate.py:55-67` | Toutes les recherches de racine supposant un checkout : `orchestrate.py:73-78`, `eval_models.py:49-55`, `context_budget.py:59`, `run_report.py:25-26`, `trajectory_guard.py:115`, `approve.sh:9`, `reject.sh:11` |
| I-15 | Emplacement des agents | `context_budget.py:27-32`, prompts `orchestrate.py:377,593` | Suivent le déplacement vers `lab/plugin/` | Chemins `root/.claude/agents/` codés en dur |
| I-16 | Sandbox | `sandbox_runner.py:112-117` (montage workspace seul), `:158-163` | Chemins relatifs au cwd en mode kit (ADR-10) | — (aucun pattern pour une instance externe) |
| I-17 | Découverte des features | `.githooks/pre-commit:24-27`, `ci_checks.sh:22-25` | Scannent déjà `examples/` | — |
| I-18 | Contenu du wheel | `pyproject.toml:12-13` | `packages = ["lab"]` embarque engine, models, templates et `lab/plugin/` | Nom/description du démo (`pyproject.toml:2,4`) |
| I-19 | Versions qui doivent concorder | `tests/sdlc_rework/test_lockfile.py:14-35` | Test de cohérence version paquet = `plugin.json` = entrée marketplace | — |
| I-20 | Constantes du moteur | `orchestrate.py:91-94` (`MAX_EVAL_RETRIES`, `MAX_PARALLEL`, `MAX_CP_REJECTS`, `BUDGET_USD`) | Deviennent des lectures de la politique effective (ADR-14) | Constantes de module figées au chargement : la politique est résolue après `--project` |
| I-21 | Règle de plan qui protège le merge | `planlint.py:265-267` (CP final/merge en `mode: auto` ⇒ erreur) | Même forme pour les clés de sécurité appliquées par plan-lint (ADR-14) ; INV-5 n'a **pas** de clé | — |
| I-22 | Refus au démarrage | `orchestrate.py:229-271` `preflight()`, `:269-270` refus sandbox + instance | Accueille `sandbox_required` / `allow_force` (ADR-14) ; le refus `:269-270` disparaît (ADR-15) | — |
| I-23 | `--force` | `orchestrate.py:986-989`, `:1035` (ignore statut `approved` + erreurs de lint) | C'est cette porte que `allow_force = false` ferme | — |
| I-24 | Montage sandbox | `sandbox_runner.py:112-115` (`-v <ws>:/workspace:rw`), `:161-164` (`add_dirs` non transmis) | Ajout d'un second montage, kit en lecture seule (ADR-15) | Transmettre des chemins hôte à l'intérieur du conteneur |
| I-25 | Paramètres d'un TOML d'instance | `lab_init.py` (écrit `.lab/lab.toml`), I-6 | `[overrides]` et `[overrides.routes]` lus avec `tomllib` (ADR-13) | Une clé inconnue ignorée en silence (I-6 `registry.py:55-56`) |
| I-26 | Phase : frontmatter | `lab/engine/plan.py:37` `parse_tasks_md` (frontmatter + nœuds) ; `orchestrate.py:1341` refuse un plan non `approved` | Même lecteur de frontmatter pour `spec.md` / `design.md` (`status: validated`) | — |
| I-27 | Phase : état de run | `orchestrate.py:1384-1422` : `state.json` relu au démarrage, tolérant à un fichier tronqué (L9), écrit par `atomic_write_json` (`:221`) | Statuts en cours d'un run | `state.json` est gitignoré : perdu avec l'environnement (lab-fix 38) ; format plat `{id: status}` sans version |
| I-28 | État dérivé de git | `planlint.py:74` `committed_task_ids` : tâches « done » lues dans `git log` (sujet canonique), « reproductible depuis un checkout frais » | Source de vérité des tâches `done` (décision Owner 1) | — |
| I-29 | Critère plan | `planlint.py:175` `validate` (DAG, IDs, recoupements, politique) | Critère de sortie « plan » tel quel | — |
| I-30 | Critères spec / design | `content_guard.py:60` `extract_content` (substance par ID) ; plan-lint vérifie déjà les IDs de spec cités par le plan | Base de spec-lint et design-lint | **Aucun spec-lint ni design-lint n'existe** |
| I-31 | Critère build | `orchestrate.py:919` `_run_task_attempts` → verify → `_eval_gate` (anti-empty-gate, couverture) → `scoped_commit` | Critère « build » existant | — |
| I-32 | Critère review | `orchestrate.py:1067` `run_review` (panel, rapport `.runs/CP-n-review.md` `:1071`), `:1137` `wait_checkpoint` | Critère « review » existant | — |
| I-33 | Signal `STATUS:` | `orchestrate.py:971` `re.search(r"STATUS:\s*(done\|blocked)([^\n]*)")` ; raison libre | Point unique où classer R3/R4/R5 | Raison en texte libre : aucune catégorie lisible par le moteur (BHV-5c) |
| I-34 | Route R1 | `orchestrate.py:929` `for attempt in range(1, MAX_EVAL_RETRIES + 1)` ; valeur lue de la politique `:399` | R1 existe déjà | — |
| I-35 | Route R7 | `orchestrate.py:1120` `parse_rejection` ; compteur `rejections` `:1383`, `:1525-1531` ; rework « OWNER REVIEW FEEDBACK » injecté | R7 existe déjà, sans reset des dépendants | Compteur en mémoire : remis à zéro à chaque redémarrage du moteur |
| I-36 | Fichier écrit par le moteur | `orchestrate.py:1071` : rapport de revue écrit dans `.runs/` ; `.gitignore` garde `.runs/*.md` versionnés « pour l'audit » | Même forme pour les propositions et les OQ | — |
| I-37 | Décision signée | `approvals.py:55` `sign`, `:79` `verify` (HMAC, identifiant libre) ; `approve.sh` / `reject.sh` | Signature d'une proposition, même jeton que les CP | — |
| I-38 | OQ d'agent | `orchestrate.py:735` (prompt de l'implementer) et `lab/plugin/agents/implementer.md:18` : « OQ-n noted in spec.md §8 » | — | **Contredit INV-10 et R3** ; cause directe du lab-fix 34 |
| I-39 | Modes de route | `policy.py:5` : `[overrides.routes]` validé R1..R7 mais appliqué à partir de l'itération 3 ; validation `:113-151` | Lecture des modes déjà en place | — |
| I-40 | Containment | `plan.py:145` `skip_dependents` | Escalade = sous-arbre `skipped`, les autres branches continuent (BHV-5a) | — |
| I-41 | Recoupement | `plan.py:140` `paths_overlap` ; `plan.py:120` `ancestors` ; `Node.implements` | Dépendants à rouvrir (fichiers **ou** IDs) | — |
| I-42 | Commit scopé | `orchestrate.py:563` `scoped_commit`, `:560` `FEATURE_ARTIFACTS = ("tasks.md",)` | Moitié « commit » d'INV-10 | La moitié « la tâche échoue si le working tree touche spec/design » n'existe pas |
| I-43 | Essai isolé | `eval_models.py:102` `call_model` (cwd dédié), `:148` `tempfile.mkdtemp(prefix="labeval-")` ; `runner.py:150` `claude_argv` (options du kit à `None` ⇒ argv sans plugin, settings ni règles) | Répertoire temporaire par lecteur | Lab-fix 19 : en essai de modèle, `--plugin-dir` / `--settings` restent des chemins du kit |
| I-44 | Lecteurs | `lab/models/registry.toml` `[roles]` ; `registry.py` `role_default` | Lecteur implementer = rôle `implementer` | **Aucun rôle `goldfish`** au registre (BHV-8e prévoit son absence) |
| I-45 | Comparaison | `evals/behavioral/cases.py:60` `verdict`, checkers `:89-162` ; `eval_models.py:276` `check_api_contract`, `:294` `check_logic` | Forme « checker → (ok, détail) » | Aucun comparateur YAML champ par champ (BHV-8a) |

I-26..I-45 : rapport design-scout de l'itération 3 ; lignes revérifiées sur `main` = `1994915`
(après les PR #4 à #12).

### 2.2 Open source / external references

| # | Problème | Référence | Pattern emprunté | Source précise |
|---|---|---|---|---|
| E-1 | Format du plugin | Claude Code — plugins reference | `.claude-plugin/plugin.json`, `agents/`, `skills/<n>/SKILL.md`, `hooks/hooks.json`, `${CLAUDE_PLUGIN_ROOT}` ; un CLAUDE.md de plugin n'est pas chargé ; `claude plugin validate --strict` | code.claude.com/docs/en/plugins-reference |
| E-2 | Un plugin peut-il porter des denies ? | idem, #settings | **Non** : seules `agent` et `subagentStatusLine` sont prises en compte | idem |
| E-3 | Bloquer une écriture depuis un plugin | Claude Code — hooks, permissions | PreToolUse exit 2 ou `permissionDecision: "deny"` ; `"onFailure": "block"` | code.claude.com/docs/en/hooks ; /permissions |
| E-4 | Échec d'un hook | Claude Code — hooks | Exit ≠ 0/2 non bloquant ; `onFailure` sans effet sur Stop | hooks #other-exit-codes, #stop |
| E-5 | Denies via `--settings` | Claude Code — settings, permissions | `--settings` au-dessus des scopes projet/utilisateur ; deny évalué en premier ; `Edit(path)` couvre tous les outils d'édition ; `**/` ancré au cwd | code.claude.com/docs/en/settings ; /permissions |
| E-6 | Options headless | Claude Code — CLI reference, headless | `--plugin-dir` (remplace un plugin installé de même nom), `--settings`, `--append-system-prompt` ; `--bare` annoncé comme futur défaut de `-p` | code.claude.com/docs/en/cli-reference ; /headless |
| E-7 | Contexte au démarrage | Claude Code — hooks #sessionstart | stdout du hook SessionStart ajouté au contexte | hooks #sessionstart |
| E-8 | Détecter un plugin | Claude Code — plugins/loading | `claude plugin list --json` ; événement `system/init` | /plugins/loading |
| E-9 | Distribution versionnée | Claude Code — marketplace reference | `.claude-plugin/marketplace.json` à la racine, source relative, `ref` par tag | /plugins/marketplace-reference |
| E-10 | Pin exact, refus nommant les deux versions | Black (MIT) | `required-version` : « The required version X does not match the running version Y! », exit 1 | `black/__init__.py:671-681` (26.10.1) |
| E-11 | Moteur en CLI | uv tools + `[project.scripts]` | `uv tool install git+<repo>@<tag>` ; `importlib.metadata.version()` | aide locale uv 0.11.32 + essai |
| E-13 | Scaffolding idempotent sans écrasement | Copier (MIT) — pattern seul, pas de dépendance | Classement create / identical / conflict avant écriture ; `--pretend` ; fichier de réponses = version du modèle épinglée dans le projet | `copier/_main.py:531-598`, `:505-512`, `:378-385` (9.19.1) |
| E-15 | Garde-fou plancher qu'un niveau inférieur ne peut qu'affiner | AWS Organizations — service control policies | Une SCP ne donne aucun droit : elle borne ; les droits effectifs d'un compte sont l'intersection de ce que permettent toutes les couches ⇒ une couche basse ne peut que **resserrer** (pour nous : plancher ⊕ override = valeur la plus stricte, clé par clé) | docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html |
| E-16 | Trois niveaux nommés et cumulatifs | Kubernetes — Pod Security Standards | `privileged` / `baseline` / `restricted` : niveaux nommés, chacun plus strict que le précédent, choisis explicitement par namespace (pour nous : `solo` / `squad` / `regulated`, choix explicite à `lab init`) | kubernetes.io/docs/concepts/security/pod-security-standards/ |
| E-17 | Monter un répertoire en lecture seule dans un conteneur | Docker — bind mounts | `-v <src>:<dst>:ro` (ou `--mount type=bind,src=…,dst=…,readonly`) : le conteneur lit, n'écrit pas | docs.docker.com/engine/storage/bind-mounts/ |
| E-18 | Budget par route, échecs non rejouables | Temporal — Retry Policies | Une politique de retry porte un nombre maximal de tentatives et une liste de types d'erreur **non rejouables**, comparés au champ `type` de l'erreur. Pour nous : R1 = retry borné ; une étiquette `OQ` / `ADR` / `scope` = type non rejouable qui sort de la boucle R1. **Écart assumé** : le défaut Temporal est « illimité », INV-4 impose un budget fini partout | docs.temporal.io/encyclopedia/retry-policies (relevé le 2026-11-14) |
| E-19 | Reset des dépendants | Apache Airflow — Dag Runs, « Re-run Tasks » | Effacer une instance de tâche remet son état à `None` et la relance ; l'option **Downstream** étend l'effacement aux tâches aval. Pour nous : BHV-6 filtre plus finement (seuls les dépendants qui recoupent fichiers ou IDs) | airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html (3.4.0, relevé le 2026-11-14) |
| E-20 | Preuve d'isolement par canari | BIG-bench (Google) — tâche `training_on_test_set` | Une chaîne GUID unique placée dans des fichiers permet de détecter qu'un modèle les a vus. Pour nous : un marqueur distinct par source interdite (BHV-8b) | github.com/google/BIG-bench/tree/main/bigbench/benchmark_tasks/training_on_test_set (relevé le 2026-11-14) |
| E-21 | Comparaison normalisée de sorties YAML (BHV-8a) | **aucune référence** | Cherchée sans résultat concluant (rapport design-scout itération 3) ⇒ ADR-24 délibéré pour ce volet | — |
| E-14 | Ajouter une recette à un justfile existant | **aucune référence** | `import` d'un `lab.just` redéfinissant `evals` casse le justfile entier (vérifié, just 1.59.0) ⇒ ADR-8 délibéré | — |

## 3. Stack

| Layer | Choice | Justified by (ref §2) |
|---|---|---|
| Runtime | Python 3.12, stdlib (`tomllib`, `importlib.metadata`, `json`, `subprocess`) ; une seule dépendance d'exécution, PyYAML, pour lire les EX (ADR-24) | NG-2 spec ; patterns I-6, I-14 |
| Packaging | hatchling, `packages = ["lab"]`, paquet `fde-kit`, CLI `lab` | I-18, E-11 |
| Agent | Claude Code CLI ≥ 2.1.295 (`onFailure`), plugin `fde-kit` | E-1, E-3, E-6 |
| Scaffolding | stdlib, pattern Copier | E-13 |
| Tests | pytest + shim `claude` existant | I-10, I-11, I-13 |
| Lecture des EX (itération 3) | PyYAML (`yaml.safe_load`), épinglé dans `uv.lock` — décision Owner (QCM 2026-11-14) : les blocs EX utilisent presque tout le YAML courant (§10, point 1) | ADR-24 |

## 4. ADRs — Architecture Decision Records

### ADR-1 — Un paquet, une version : moteur + plugin dans `fde-kit`
- **Status:** accepted
- **Context:** le kit doit voyager avec le FDE (OQ-1) et le run doit utiliser exactement le
  plugin de la version épinglée (INV-7). Deux artefacts versionnés séparément dériveraient.
- **Decision:** le plugin vit sous `lab/plugin/` (`.claude-plugin/plugin.json`, `agents/`,
  `skills/`, `hooks/`, `rules/`). Le wheel `fde-kit` (`packages = ["lab"]`) embarque moteur et
  plugin. Le repo est sa propre marketplace (`.claude-plugin/marketplace.json` à la racine,
  source `./lab/plugin`). Un test de cohérence impose version `pyproject.toml` = `plugin.json` =
  entrée marketplace. CLI `lab` (`[project.scripts]`) : `init`, `run` et `validate` (relais vers
  l'orchestrateur), `version`. Installation : `uv tool install git+<url-du-repo-kit>@v<x.y.z>`.
- **Anchored on:** E-1, E-9, E-11, I-18, I-19.
- **Alternatives considered:** plugin dans un repo séparé (rejeté : deux versions à synchroniser) ;
  plugin à la racine `plugin/` (rejeté : hors du wheel, il faudrait un `force-include`).
- **Consequences:** le nom de paquet top-level `lab` est générique ; acceptable dans le venv
  isolé d'un `uv tool`, à revoir si le kit devient une dépendance importée.

### ADR-2 — Runs orchestrés : le moteur fournit plugin, interdictions et règles à chaque appel
- **Status:** accepted (décision Owner : `--plugin-dir` explicite)
- **Context:** `--add-dir` ne charge ni hooks ni denies ; un plugin ne peut pas porter de denies ;
  le chargement implicite des plugins utilisateur par `-p` risque de disparaître (`--bare`).
- **Decision:** `claude_argv` (constructeur unique) ajoute, quand le moteur le demande :
  `--plugin-dir <lab/plugin>`, `--settings <lab/engine/run_settings.json>` (uniquement les deux
  denies `Edit(**/.approvals/**)` et `Edit(**/.runs/**)`, **aucun hook**), et
  `--append-system-prompt <contenu de lab/plugin/rules/hard-rules.md>`. Le moteur ne passe
  jamais `--bare`. Aucun garde-fou de run ne dépend d'un hook : l'eval gate de run reste
  `_eval_gate` du moteur (`orchestrate.py:424-459`) ; le hook Stop du plugin est un plus.
- **Anchored on:** I-1, I-2, E-5, E-6.
- **Alternatives considered:** plugin installé chez l'utilisateur + `claude plugin list --json`
  (rejeté par l'Owner : dépend du comportement implicite de `-p`) ; `--append-system-prompt-file`
  (rejeté : documenté mais absent de l'aide locale, non exercé).
- **Consequences:** BHV-2a s'interprète ainsi : « plugin absent » = `lab/plugin/` introuvable dans
  le kit installé (installation cassée) ; « version ≠ pin » = version du kit ≠ `kit_version`.
  `--plugin-dir` remplace un plugin installé de même nom : pas de double chargement.

### ADR-3 — Une seule source pour les règles dures
- **Status:** accepted (décision Owner : `plugin/` source unique)
- **Context:** ADR-5 de sdlc-rework interdit une seconde source de vérité ; l'instance ne doit
  contenir aucun fichier de règles (INV-8).
- **Decision:** la méthode portable (les 3 artefacts, règles dures, vocabulaire) va dans
  `lab/plugin/rules/hard-rules.md`. Elle est injectée par le hook SessionStart du plugin
  (sessions interactives, BHV-2b) et par `--append-system-prompt` (runs, ADR-2). Le
  `CLAUDE.md` du kit ne garde que ce qui est propre au repo du kit (stack, langue, brand guard,
  développement du kit) et pointe vers le fichier de règles. Le `.claude/` du kit disparaît :
  on développe le kit avec `--plugin-dir lab/plugin`. Les agents `.md` sont déplacés sans
  modification de contenu (forme) ; toute modification de contenu suit la boucle
  `lab/models/EVOLUTION.md`. La status line (`.claude/statusline.py`) part dans
  `lab/plugin/statusline.py` : un plugin ne peut pas définir la status line principale (E-2), le
  FDE la câble une fois dans ses réglages utilisateur (OQ-9).
- **Anchored on:** I-12, E-7.
- **Alternatives considered:** garder les règles dans CLAUDE.md et les faire lire par le plugin
  (rejeté par l'Owner : le kit ne se développerait pas avec son propre outillage).
- **Consequences:** `tests/sdlc_rework/test_agents_md.py:21` compare la taille d'AGENTS.md à
  celle de CLAUDE.md : la comparaison se fait désormais au fichier de règles (le contrat EVAL-5
  de sdlc-rework, « pointe vers CLAUDE.md sans dupliquer de règle », est inchangé). Le canal de
  livraison des règles change ⇒ ré-évaluation de la chaîne de commandement (ADR-11).

### ADR-4 — Garde-fous interactifs portés par les hooks du plugin
- **Status:** accepted
- **Context:** en session interactive, le plugin ne peut pas déclarer de denies (E-2) et les
  hooks actuels échouent ouverts en instance (I-4).
- **Decision:** `lab/plugin/hooks/hooks.json` déclare : `PreToolUse` sur
  `Edit|Write|MultiEdit|NotebookEdit` → `guard_paths.sh` (exit 2 si `tool_input.file_path` est
  sous `.approvals/` ou `.runs/`, `"onFailure": "block"`) ; `SessionStart` → affiche les règles ;
  `Stop`/`SubagentStop` → `eval_gate.sh` ; `PostToolUse` → lint. Tous référencés via
  `"${CLAUDE_PLUGIN_ROOT}"/hooks/…`. `eval_gate.sh` se déclenche aussi quand `.lab/lab.toml`
  existe (plus de sortie silencieuse sans `pyproject.toml`). Les entrées de deny inertes
  disparaissent avec le `.claude/settings.json` du kit.
- **Anchored on:** E-3, E-4, E-7, I-4, I-10.
- **Alternatives considered:** aucune côté plugin (E-2).
- **Consequences:** une écriture par sous-processus (script Python lancé via Bash) n'est pas
  bloquée : limite connue du modèle de confiance (README), la sandbox reste la vraie frontière.

### ADR-5 — Le kit retrouve sa racine, qu'il soit cloné ou installé
- **Status:** accepted
- **Context:** installé par `uv tool`, `_repo_root()` remonte jusqu'à `site-packages` et le
  registre se charge vide sans erreur (constat design-scout).
- **Decision:** racine du kit = `LAB_ROOT` si défini (seam de test conservé), sinon
  `Path(__file__).resolve().parents[2]` si elle contient le marqueur `lab/models/registry.toml`
  (vrai dans un checkout comme dans `site-packages`), sinon erreur rc 1. Toutes les recherches
  listées en I-14 passent par une fonction unique. Version du kit lue via
  `importlib.metadata.version("fde-kit")`, avec repli sur `pyproject.toml` dans un checkout.
- **Anchored on:** I-14, E-11.
- **Consequences:** `load_registry` garde son repli « registre vide » pour le seam de test
  uniquement.

### ADR-6 — Pré-vol fail-closed : versions et combinaisons interdites
- **Status:** accepted
- **Context:** BHV-2a, INV-7 ; une CLI trop ancienne ignore `onFailure`.
- **Decision:** avant le verrou, `lab run --project <instance>` vérifie dans l'ordre : racine du
  kit résolue (ADR-5) ; `lab/plugin/` présent ; `.lab/lab.toml` présent et `kit_version` =
  version du kit, sinon rc 1 avec le message de la spec EX-5 « plugin X ≠ pinned kit Y » ; `claude --version` ≥ 2.1.295 ;
  combinaison runner/instance autorisée (ADR-10). En mode kit (sans `--project`), seules les
  vérifications de racine, de plugin et de CLI s'appliquent.
- **Anchored on:** E-10 (forme du message), I-5.
- **Alternatives considered:** version minimale seulement (pre-commit, `minimum_pre_commit_version`)
  — rejeté : INV-7 demande un pin exact.

### ADR-7 — `lab init` : plan d'abord, jamais d'écrasement
- **Status:** accepted
- **Decision:** `lab init <project> --profile <p> [--dry-run]` (`--profile` obligatoire : absent ⇒ rc 1
  listant `solo`, `squad`, `regulated` — le niveau de contrôle est toujours un choix explicite, OQ-11) calcule le plan complet, classe
  chaque fichier (`create` / `identical` / `skip` — jamais `overwrite`), l'affiche une ligne par
  fichier, puis l'applique sauf en `--dry-run`. Fichiers : `.lab/lab.toml`
  (`schema_version = 1`, `kit_version`, `profile`), `work/README.md` et `work/_templates/{spec,design,tasks}.template.md` (jamais nommés
  `spec.md`/`design.md`/`tasks.md` : le pre-commit et `ci_checks.sh` prendraient `work/` pour une
  feature et plan-lint rejette le modèle brut — OQ-10), et
  les recettes du justfile (ADR-8). Rien sous `.claude/`, pas de `CLAUDE.md`/`AGENTS.md`, pas
  de workflow CI (INV-8). Second lancement : tout est `identical` ⇒ « 0 changement ».
  Profils acceptés en itération 1 : `solo`, `squad`, `regulated` (valeur seulement enregistrée ;
  son effet arrive avec l'itération 2).
- **Anchored on:** E-13, I-6, I-7, I-13.

### ADR-8 — Recettes d'evals dans un justfile existant (sans référence — délibéré)
- **Status:** accepted
- **Context:** E-14 ; BHV-1b, BHV-1e.
- **Decision:** justfile absent ⇒ créé depuis un modèle. Justfile présent ⇒ lu avec
  `just --justfile <project>/justfile --dump --dump-format json` (fichier explicite : pas de
  remontée vers un justfile parent) ; erreur de parse ⇒ rc 1 sans rien écrire ; recette
  présente ⇒ conservée telle quelle ; recette absente ⇒ ajoutée **en fin de fichier**, puis
  nouvelle lecture ; en cas d'échec, les octets d'origine sont restaurés. Modèles : instance
  Python (`pyproject.toml` présent) ⇒ `uv run pytest -m eval` (rc 5 ⇒ message, rc 0 ; l'anti-gate-vide
  du moteur reste l'autorité) ; sinon ⇒ recettes qui échouent fermées : « no evals configured —
  define `evals` and `evals-collect` », rc 1.
- **Alternatives considered:** `import 'lab.just'` (rejeté : redéfinition ⇒ justfile cassé, vérifié).

### ADR-9 — Les exemples sont des instances autonomes
- **Status:** accepted (décision Owner)
- **Decision:** `examples/devis/` (features `devis-pose`, `export-devis`) et `examples/booking/`
  (`salle-booking`), chacun avec son `pyproject.toml`, son `uv.lock`, son `.lab/lab.toml` (profil `squad`, OQ-11) et son
  justfile **produits par `lab init`**, ses `work/`, `src/`, `tests/` et ses docs produit
  (`docs/export-notes.md`, `docs/export-usage.md` partent dans `examples/devis/docs/`). Pilotés par
  `lab run --project examples/<x>`. Les chemins `files_touched`/`verify` des triplets restent
  valides, relatifs à la racine de l'exemple. Le kit garde `work/sdlc-rework` et `work/fde-kit`.
  Le `pyproject.toml` du kit devient `fde-kit` (nouveau `uv.lock` dans le même commit). `gate-ci`
  boucle sur les exemples (`just examples-gate` : `uv sync --locked` + `just evals` par exemple).
  Valeurs par défaut retenues sans QCM :
  - `evals/golden/devis-calc` reste une fixture du kit (évaluation des modèles) ; son test
    d'intégrité lit l'implémentation de référence dans `examples/devis/src/devis/calc.py`.
  - `brand_guard` scanne `examples/` (livré avec le kit, doit rester générique) ; seuls les
    `assets/` restent exclus. `.gitignore` passe de `work/**/assets/` à `**/work/**/assets/`.
  - Les docs du kit qui citent les exemples (tutoriel, format de commit, etc.) gardent leurs
    exemples et pointent vers `examples/` ; pas de réécriture générique.
- **Anchored on:** I-17, I-18, I-13 ; dogfooding de `lab init` et de `--project`.
- **Consequences:** `content_guard` voit les fichiers déplacés comme nouveaux : le commit de
  migration est un déplacement pur (`git mv`, aucune modification de contenu), relu au checkpoint.

### ADR-10 — Sandbox en itération 1 : mode kit conservé, instance externe refusée
- **Status:** superseded by ADR-15 (itération 2) — accepted (décision Owner) pour l'itération 1
- **Context:** le conteneur ne monte que le répertoire de travail, avec un home vide (I-16).
- **Decision:** en mode kit, le moteur passe plugin et settings en **chemins relatifs au cwd**
  (`lab/plugin`, `lab/engine/run_settings.json`), valides sur l'hôte comme dans `/workspace` :
  la sandbox du kit continue de fonctionner. `LAB_RUNNER=sandbox` avec `--project` ⇒ pré-vol
  rc 1 : « sandbox + external instance not supported before iteration 2 ». INV-1 est tenu par
  le refus. Le support (montage en lecture seule du kit) arrive avec l'itération 2, dont le
  profil `regulated` exige la sandbox.

### ADR-11 — La gouvernance des modèles mesure le contexte de production
- **Status:** accepted
- **Context:** `eval_models.py:83-99,132-148` construit son propre argv, sans règles ni agents :
  la couche chaîne de commandement (éliminatoire) ne teste pas le canal de livraison des règles,
  qui change avec ADR-2/ADR-3.
- **Decision:** `eval_models.py` construit ses appels via `claude_argv` avec les mêmes options
  qu'un run (ADR-2). Avant la première utilisation réelle du kit sur une mission, une campagne
  live des couches behavioral + chain est exécutée et relue (checkpoint humain, facturé).
- **Anchored on:** `lab/models/EVOLUTION.md` (boucle evals → scaffolding), I-1.

### ADR-12 — Banc d'évaluation des modèles : spike promptfoo (itération multi-outils)
- **Status:** proposed — spike à mener dans l'itération multi-outils (BHV-11), décision sur preuve
- **Context:** la campagne du 2026-11-12 a montré trois défauts du banc maison (`eval_models.py`) :
  un appel en erreur (quota, API) compté comme un échec du modèle — y compris 3 fausses violations
  de chaîne de commandement —, un seul essai par tâche, et pas de distinction erreur/échec. BHV-11
  exigera en plus un runner par outil (Copilot, opencode, Codex CLI).
- **Decision:** spike : ré-exprimer les 14 cas existants dans promptfoo — nos fixtures et nos
  fonctions `check()` restent la source unique, branchées en provider et assertions personnalisés —
  puis rejouer la même campagne. Adoption si promptfoo est au moins aussi strict (même verdicts,
  chaîne éliminatoire conservée) et moins coûteux à maintenir ; sinon, correction du banc maison.
  La logique propre au lab (éliminatoire, recommandation par rôle, séparation des tâches,
  promotion `[roles]`) reste un post-traitement du lab dans les deux cas.
- **Anchored on:** promptfoo (outil open source d'évaluation et de red-teaming de LLM : matrice
  fournisseurs × cas, répétitions, cache, distinction erreur/échec, providers personnalisés) —
  référence précise (version, licence, fichiers) à collecter par design-scout avant le spike.
- **Alternatives considered:** garder et corriger le banc maison (option de repli du spike).
- **Consequences:** chaîne d'outils Node.js en plus du stack Python (verrouillage des versions à
  prévoir, comme `uv.lock`) ; télémétrie et partage de résultats à désactiver explicitement pour les
  missions client.

### ADR-13 — Politique effective : plancher monotone ⊕ overrides, clé par clé
- **Status:** accepted
- **Context:** BHV-3 / INV-2 : trois profils nommés, une instance peut durcir, jamais assouplir ; les
  clés libres (performance, coût) restent réglables.
- **Decision:** les profils sont des **données** : `lab/engine/policy_profiles.toml`
  (`schema_version = 1`), une entrée par clé avec `kind = "safety" | "free"`, la direction stricte
  (`strict = "true" | "false" | "up" | "down"`) et la valeur par profil — la table de BHV-3 telle
  quelle. Module `lab/engine/policy.py` : `effective_policy(lab_toml) -> {key: (value, origin)}` où
  `origin ∈ {floor, override, override (free key)}`. Clé de sécurité : override accepté seulement
  s'il est au moins aussi strict que le plancher, sinon rc 1 avec le message d'EX-1
  (`<key>=<v> is looser than floor '<profile>' (<floor>)`, BHV-3a). Clé inconnue (y compris
  sous `[overrides.routes]`) : rc 1 (BHV-3b). `goldfish_min_score` est déclarée, « non déclarée »
  par défaut, sans effet avant l'itération 3. Commande `lab policy [--project p]` : une ligne par
  clé, valeur et origine. **Aucune clé ne touche au merge** (INV-5) : il n'y a pas de clé à
  durcir ou assouplir, la règle reste dans plan-lint (I-21).
- **Routes (décision Owner) :** `[overrides.routes]` est réservé dès l'itération 2 : `R1`..`R7`
  connues, valeur `auto | proposal | human` ; `auto` sur R2, R3, R4 ou R5 ⇒ rc 1 (BHV-3c, INV-3) ;
  une route inconnue ⇒ rc 1. Les modes sont validés et affichés par `lab policy` mais **appliqués
  à partir de l'itération 3** (BHV-5), ce que l'affichage dit.
- **Anchored on:** E-15 (intersection : une couche basse ne peut que resserrer), E-16 (niveaux nommés
  cumulatifs, choix explicite), I-6 / I-25 (TOML + `schema_version`, jamais de clé ignorée).

### ADR-14 — Chaque clé a un seul point d'application, mécanique
- **Status:** accepted
- **Decision:** la politique effective est résolue **une fois**, au démarrage (après `--project`),
  et chaque clé est appliquée là où BHV-3 l'indique, jamais deux fois :
  - **plan-lint** (erreur) : `auto_checkpoints_allowed = false` ⇒ tout CP `mode: auto` ;
    `min_reviewers` ⇒ un CP dont `reviewers` est inférieur ; `max_tasks_between_checkpoints` ⇒
    plus de N tâches entre deux CP sur un chemin du graphe (I-21) ;
  - **pré-vol** (rc 1, avant le verrou, I-22) : `sandbox_required = true` ⇒ `LAB_RUNNER=sandbox`
    exigé ; `allow_force = false` ⇒ `--force` refusé (I-23) ;
  - **moteur** : `max_task_attempts`, `max_parallel`, `max_cp_rejects`, `budget_usd` remplacent les
    constantes de module (I-20). `LAB_BUDGET_USD` reste un réglage opérateur de cette clé libre
    (prioritaire s'il est posé) ; la politique fournit la valeur par défaut.
  **INV-5 a deux points d'application, volontairement** : plan-lint refuse un CP final/merge en
  `mode: auto` (I-21), **et** le moteur refuse à l'exécution de l'auto-valider, quels que soient son
  `mode`, `--force` ou le profil (`is_merge_checkpoint`, même test que plan-lint). Le second existe
  parce que `--force` ignore les erreurs de lint et qu'`allow_force` est vrai en `solo`/`squad` : un
  seul point laissait une clé de profil ouvrir un merge automatique (revue CP-7). Exception assumée
  au « un seul point par clé » : INV-5 n'est pas une clé, c'est une règle dure.
  plan-lint reçoit la politique effective en paramètre (fonction pure, comme le registre) : sans
  instance (tests, `lab validate` hors projet), le profil `squad` documenté sert de valeur d'essai,
  jamais pour un run réel (ADR-16).
- **Anchored on:** I-20, I-21, I-22, I-23 (formes existantes de règle, de refus et de lecture).

### ADR-15 — Sandbox pour une instance externe : kit monté en lecture seule
- **Status:** accepted (décision Owner) — remplace ADR-10
- **Decision:** avec `--project`, le runner sandbox monte **deux** répertoires : l'instance en
  `/workspace` (lecture-écriture, cwd de l'agent) et la racine du kit en `/kit` **en lecture
  seule** (E-17). Le moteur passe alors `--plugin-dir /kit/lab/plugin`,
  `--settings /kit/lab/engine/run_settings.json`, et traduit les `add_dirs` qui pointent dans le
  kit vers `/kit/…` ; tout autre chemin hôte reste refusé (I-24). Le refus d'ADR-10 disparaît du
  pré-vol. Mode kit inchangé (chemins relatifs, ADR-10). Les tests d'argv restent sans Docker ;
  un essai Docker réel est un contrôle de checkpoint, pas un test du gate.
- **Anchored on:** I-16, I-24, E-17.

### ADR-16 — Le kit est une instance de lui-même
- **Status:** accepted (décision Owner)
- **Decision:** le repo du kit reçoit son propre `.lab/lab.toml` (`profile = "squad"`,
  `kit_version` = version du kit) ; le mode kit lit la politique comme une instance. Un run réel
  sans `.lab/lab.toml` ⇒ pré-vol rc 1 (« le niveau de contrôle est toujours un choix explicite »,
  OQ-11) — y compris en mode kit. Les bacs à sable de test écrivent leur `.lab/lab.toml`.
- **Anchored on:** ADR-7 (le même fichier, écrit par `lab init`), ADR-9 (exemples = instances).

### ADR-17 — `lab next` : phase déduite, un critère de sortie par phase
- **Status:** proposed (amendement 0.7.0)
- **Context:** BHV-4 ; aujourd'hui seul le plan a un critère mécanique (plan-lint) et seul le build
  a une exécution (`orchestrate.py`).
- **Decision:** `lab next <feature> [--project p]` lit, dans l'ordre : `status:` de `spec.md`,
  de `design.md` et de `tasks.md` (même lecteur de frontmatter, I-26), puis l'état de run (ADR-18).
  La phase courante est la première dont le critère de sortie n'est pas vert :

  | Phase | Critère de sortie (mécanique) | Point d'application | Si vert / si rouge |
  |---|---|---|---|
  | spec | spec-lint (ADR-19) ; test goldfish (ADR-24), bloquant seulement si `goldfish_min_score` est déclaré | `lab spec-lint`, `lab goldfish` | rouge : affiche la décision Métier attendue |
  | design | design-lint (ADR-19) + `status: validated` | `lab design-lint` | rouge : affiche la décision FDE attendue |
  | plan | plan-lint vert avec la politique effective + `status: approved` | `planlint.validate` (I-29) | rouge : affiche la décision Owner attendue |
  | build | toutes les tâches `done` (ADR-18) | boucle existante (I-31) | lance `lab run` |
  | review | checkpoints signés | `wait_checkpoint` (I-32) | affiche `approve.sh` / `reject.sh` |
  | merge | — | — | affiche « merge : décision Owner » (INV-5) |

  `lab next` n'écrit rien quand il ne lance rien : deux appels successifs sans changement donnent la
  même sortie (idempotence, EVAL-4). Quand il lance une étape agent, il délègue à la commande
  existante (`lab run`), jamais à un second moteur. La sortie nomme toujours qui décide, quoi, et
  la commande à lancer.
- **Anchored on:** I-26, I-29, I-31, I-32.
- **Alternatives considered:** un fichier d'état de phase séparé (rejeté : une seconde source de
  vérité à côté des frontmatters et de `state.json`).
- **Consequences:** EVAL-4 = 6 triplets fixtures, un par phase, sous `tests/fde_kit/`.

### ADR-18 — État de run : git pour les tâches `done`, `state.json` pour le reste
- **Status:** proposed (décision Owner 1 et 4, QCM du 2026-11-14)
- **Context:** `state.json` est gitignoré et se perd avec l'environnement (I-27, lab-fix 38) ; git
  porte déjà les tâches livrées (I-28). Le compteur de rejets vit en mémoire (I-35).
- **Decision:** une tâche est `done` si elle a un commit au sujet canonique dans l'historique git
  (`committed_task_ids`, I-28) **et** n'est pas rouverte dans `state.json`, ou si `state.json` la
  dit `done`. `state.json` passe à un format versionné qui porte ce que git ne voit pas :
  statuts en cours, tâches rouvertes (R7, ADR-23), compteur de rejets par CP (décision Owner 4),
  budget consommé par route (INV-4, même raison que le compteur). Un `state.json` à l'ancien format
  plat `{id: status}` est relu comme `tasks` ; illisible ⇒ repli sur git seul (au lieu de « tout
  `pending` » aujourd'hui, I-27). Un checkpoint n'a pas de commit : son état reste celui de
  `state.json` et des jetons `.approvals/`.
- **Anchored on:** I-27, I-28.
- **Alternatives considered:** `state.json` seul (rejeté par l'Owner : perdu avec l'environnement) ;
  git seul (rejeté par l'Owner : ne porte ni l'en-cours, ni les compteurs).
- **Consequences:** le compteur de rejets et les budgets de route survivent à un redémarrage du
  moteur, pas à la perte de l'environnement (`state.json` reste gitignoré) ; dans ce cas ils
  repartent de zéro, ce que le moteur affiche. BHV-4 (spec 0.9.0) nomme l'historique git à côté des
  frontmatters et de `state.json`.

### ADR-19 — spec-lint et design-lint : deux recettes, un critère par phase
- **Status:** proposed (décision Owner 5, QCM du 2026-11-14)
- **Decision:** deux modules séparés, `lab/engine/speclint.py` et `lab/engine/designlint.py`,
  chacun fonction pure + CLI (rc 0/1, une ligne par écart), exposés comme `lab spec-lint <feature>`
  / `lab design-lint <feature>` et recettes `just spec-lint` / `just design-lint`. Ils réutilisent
  l'extraction par ID de `content_guard` (I-30) et le lecteur de frontmatter (I-26).
  - **spec-lint** (BHV-4) : IDs uniques ; chaque BHV et INV couvert par au moins un EVAL (colonne
    *Covers* du §7) ; 0 OQ ouverte (une OQ est fermée quand sa ligne porte « résolue ») ;
    `status: validated`.
  - **design-lint** (BHV-4) : chaque ADR non `superseded` porte une ligne `Anchored on:` citant au
    moins un ID I-n ou E-n défini en §2, **ou** se déclare « sans référence — ADR délibéré ».
- **Anchored on:** I-29 (forme de plan-lint : fonction pure, une ligne par écart), I-30.
- **Alternatives considered:** étendre plan-lint par sous-commandes (rejeté par l'Owner : un
  module couvrirait trois phases).
- **Consequences:** les designs existants (ADR-10 n'a pas de ligne `Anchored on:`, ADR-8 dit « sans
  référence — délibéré ») sont passés au design-lint avant l'activation du critère ; chaque écart
  est corrigé par amendement, jamais en relâchant la règle.

### ADR-20 — Un seul classifieur de signaux, catégorie `STATUS:` structurée
- **Status:** proposed (décision Owner 2, QCM du 2026-11-14)
- **Context:** BHV-5, BHV-5c ; la raison d'un `STATUS: blocked` est aujourd'hui du texte libre lu
  en un seul endroit (I-33).
- **Decision:** grammaire de fin de réponse : `STATUS: done` ou
  `STATUS: blocked — <OQ|ADR|scope>: <raison>`. Une fonction pure
  `classify(signal) -> (route, détail)` est le seul point qui choisit une route :

  | Signal | Route |
  |---|---|
  | verify/eval rouge, tentative < `max_task_attempts` | R1 |
  | verify/eval rouge à la dernière tentative | R2 |
  | `STATUS: blocked — OQ: …` | R3 |
  | `STATUS: blocked — ADR: …` | R4 |
  | `STATUS: blocked — scope: …` | R5 |
  | verdict agrégé `BLOCK` du panel sur un CP `mode: auto` | R6 |
  | rejet signé de l'Owner (`reject.sh`) | R7 |
  | `STATUS: blocked` sans catégorie reconnue | `human` (BHV-5c) |

  Le mode de chaque route vient de la politique effective (`[overrides.routes]`, I-39), désormais
  appliquée ; la note « appliqué à partir de l'itération 3 » de `lab policy` disparaît. Le message
  de fuite de scope du moteur (`STATUS: blocked — files_touched gap: <files>`, `orchestrate.py`
  `_run_task_attempts`) devient `STATUS: blocked — scope: files_touched gap: <files>`.
- **Anchored on:** I-33, I-34, I-39, E-18 (types d'erreur non rejouables, comparés à un champ
  `type` déclaré).
- **Alternatives considered:** texte libre classé par mots-clés (rejeté par l'Owner : un mot-clé
  manqué produit une route fausse au lieu de `human`).
- **Consequences:** la grammaire change le prompt de l'implementer et `implementer.md` (ADR-22) ; les
  cas behavioral qui lisent `STATUS:` (`evals/behavioral/cases.py` `is_blocked`) sont mis à jour
  dans le même lot et le changement d'instrument est re-mesuré (campagne facturée, smoke d'abord).

### ADR-21 — Propositions écrites par le moteur, appliquées après décision signée
- **Status:** proposed (amendement 0.7.0)
- **Context:** INV-3, INV-4, BHV-5a, BHV-5b ; routes R2, R4, R5.
- **Decision:** pour R2, R4 et R5, le moteur écrit `.runs/<Tn>-<Rn>-<sujet>.md` (ex. EX-2 :
  `.runs/T4-R2-plan-delta.md`) : signal déclencheur, extrait de la réponse de l'agent, proposition
  (diff de `tasks.md` limité aux nœuds non démarrés pour R2/R5 ; rapport design-scout pour R4) et la
  commande de décision. La tâche passe `failed` ou `blocked`, ses dépendants `skipped`
  (`skip_dependents`, I-40), les autres branches continuent (BHV-5a). Aucun artefact humain n'est
  modifié (INV-3, quel que soit le profil). La décision est un jeton signé du même type qu'un
  checkpoint, sur l'identifiant de la proposition (`approve.sh T4-R2 <feature>`, I-37). Au
  redémarrage, une proposition approuvée est appliquée **par le moteur** (diff de `tasks.md`), puis
  le run reprend sur le graphe amendé sans rejouer les tâches `done` hors delta (ADR-18, BHV-5b).
  Budgets : R2, R4, R5 = 1 ; R6 = 1 puis `human` ; R7 = `max_cp_rejects` ; consommés et persistés
  dans `state.json` (ADR-18). Budget épuisé ⇒ escalade humaine (INV-4). R6 (nouveau) : un `BLOCK`
  sur un CP `auto` réinjecte le rapport du panel comme rework des tâches du CP, une fois.
- **Anchored on:** I-36 (fichier écrit par le moteur dans `.runs/`, versionné pour l'audit), I-37,
  I-40, E-18 (budget fini, contrairement au défaut illimité de Temporal).
- **Alternatives considered:** proposition appliquée automatiquement en `solo` (exclu par INV-3 et
  BHV-3c).
- **Consequences:** un `tasks.md` `approved` n'est modifié que par le moteur, après signature ;
  plan-lint revalide le graphe amendé avant la reprise.

### ADR-22 — R3 : l'OQ passe par le moteur ; INV-10 vérifié avant chaque commit
- **Status:** proposed (décision Owner 3, QCM du 2026-11-14 : dans l'itération 3, avec R3)
- **Context:** le prompt de l'implementer (`orchestrate.py:735`) et `implementer.md:18` font écrire
  l'OQ dans `spec.md` §8 (I-38), contre INV-10 et R3 ; cause du lab-fix 34. INV-10 n'a que sa
  moitié « commit » (I-42).
- **Decision:** dans le même lot : (1) le prompt et `implementer.md` demandent de formuler l'OQ
  dans la réponse et de finir par `STATUS: blocked — OQ: <question>` ; le changement d'agent suit
  la boucle `lab/models/EVOLUTION.md` ; (2) sur R3, le moteur écrit `.runs/<Tn>-OQ.md` et notifie
  la tâche et ses dépendants impactés (EX-3) ; (3) avant `scoped_commit`, le moteur compare
  `spec.md` et `design.md` au HEAD : tout écart ⇒ la tâche échoue, rien n'est commité (EVAL-9).
- **Anchored on:** I-36, I-38, I-42.
- **Alternatives considered:** corriger le prompt seul, tout de suite (rejeté par l'Owner : une OQ
  n'aurait plus de destination avant R3).
- **Consequences:** `spec.md` reste octet pour octet identique pendant un run (EX-3) ; l'Owner
  intègre l'OQ par amendement versionné.

### ADR-23 — Reset ciblé : recoupement de fichiers ou d'IDs
- **Status:** proposed (amendement 0.7.0)
- **Context:** BHV-6 ; aujourd'hui R7 remet en `pending` les tâches visées, sans regarder leurs
  dépendants (I-35).
- **Decision:** quand R7 rouvre une tâche T, le moteur parcourt ses dépendants transitifs `done`
  (hors checkpoints, via `ancestors`, I-41) ; un dépendant repasse `pending`, avec la note de
  rework « amont <Tn> modifié », si un de ses `files_touched` recoupe un de ceux de T
  (`paths_overlap`, I-41) **ou** s'il partage un ID de `implements`. Les autres restent `done` et
  sont listés dans la notification (« <Tn> non relancé : aucun recoupement », BHV-6a). Les tâches
  rouvertes sont marquées dans `state.json` (ADR-18), qui l'emporte alors sur git. Le filet de
  sécurité est l'eval globale déjà lancée par `wait_checkpoint` au CP suivant (BHV-6b, I-32).
- **Anchored on:** I-35, I-41, E-19 (Airflow « Downstream » : effacement de tout l'aval ; BHV-6
  filtre plus finement).
- **Consequences:** EX-7 se teste sans agent, sur le graphe seul (EVAL-6).

### ADR-24 — Test goldfish : spec masquée, deux lecteurs isolés, canaris
- **Status:** proposed (décision Owner 6, QCM du 2026-11-14) — volet comparaison : sans référence —
  ADR délibéré (E-21)
- **Context:** BHV-8, BHV-8a..8e, INV-12, EX-8.
- **Decision:** `lab goldfish <feature> [--project p]`, en lecture seule :
  1. **Masquage** : copie de `spec.md` où chaque `expected_output` des EX est remplacé par un
     marqueur neutre ; un contrôle refuse la copie si une valeur attendue y subsiste.
  2. **Lecteurs** : le petit lecteur (rôle `goldfish` du registre) et le lecteur implementer (rôle
     `implementer`), chacun dans son propre `tempfile.mkdtemp` **hors de tout dépôt git** ne
     contenant que la copie masquée (I-43). Appel via `claude_argv` sans les options du kit, plus
     `--safe-mode` (ni `CLAUDE.md`, ni plugins installés, ni hooks, avec l'authentification normale)
     et `--tools ""` (aucun outil) ; la copie masquée est passée dans le prompt. `--bare` est
     écarté : il n'accepte pas l'authentification OAuth. Même modèle pour les deux rôles, ou rôle
     absent ⇒ un seul appel et la note « lecteurs confondus — signal `fragile` indisponible »
     (BHV-8e).
  3. **Preuve d'isolement** (BHV-8b, spec 0.9.0), un marqueur distinct tiré à chaque test par source :
     règles dures — un plugin leurre passé par `--plugin-dir`, dont le hook `SessionStart` (le canal
     des règles en session) émet le marqueur ; `CLAUDE.md` — un fichier portant le marqueur dans le
     parent du répertoire du lecteur ; git — `git rev-parse --is-inside-work-tree` doit échouer dans
     le répertoire du lecteur, vérifié avant l'appel. Marqueur présent dans une réponse, ou
     répertoire dans un dépôt ⇒ rc 1, test invalide, aucun score (INV-12).
  4. **Comparaison** (BHV-8a) : blocs EX lus par `yaml.safe_load` ; un document `---` dont l'`input`
     contient `same` reprend l'`input` du document précédent, surchargé par ses autres clés (forme
     d'EX-8) ; non résoluble ⇒ « non testable ». Mapping comparé champ par champ, scalaire comparé seul, après
     normalisation (casse, espaces, types numériques : `37.2` = `37.20`) ; toute autre forme =
     « non testable », affichée et exclue du score. Fonction pure, forme « checker → (ok, détail) »
     (I-45).
  5. **Rapport** : score par lecteur, signal croisé par EX testable, écarts (ID, lecteur, champs),
     non testables ; rc selon BHV-8c / 8d.
  **Rôle `goldfish` (décision Owner 6)** : Haiku 5.5, seul modèle tier `fast` du registre, reçoit
  l'éligibilité `goldfish` ; une campagne d'évaluation facturée (smoke d'abord, accord de l'Owner
  avant le run complet) précède son affectation dans `[roles]`. D'ici là, BHV-8e s'applique.
- **Anchored on:** I-43, I-44, I-45, E-20 ; comparaison : sans référence — ADR délibéré (E-21).
- **Alternatives considered:** rôle `goldfish` affecté sans campagne (rejeté par l'Owner : un rôle
  ne change que sur preuve mesurée) ; rôle reporté (rejeté par l'Owner).
- **Consequences:** `claude_argv` (I-1) gagne deux options, `safe_mode` et `tools`, à `None` par
  défaut (argv inchangé pour tous les autres appels). `--safe-mode` est présent dans l'aide de la
  CLI 2.1.323, où les smokes ont été faits : `lab goldfish` refuse (rc 1) une CLI plus ancienne,
  même forme que le pré-vol (ADR-6). PyYAML devient la seule dépendance d'exécution du paquet.

## 5. Contracts & data

- **`.lab/lab.toml`** (instance) :
  ```toml
  schema_version = 1
  kit_version = "0.1.0"   # pin exact (INV-7), comparé à la version du kit installé
  profile = "squad"       # solo | squad | regulated — plancher (ADR-13)

  [overrides]             # optionnel : durcir une clé de sécurité, régler une clé libre
  min_reviewers = 2
  max_parallel = 4

  [overrides.routes]      # optionnel : R1..R7 = auto | proposal | human (appliqué en itération 3)
  R6 = "human"
  ```
- **`lab/engine/policy_profiles.toml`** (kit, ADR-13) : une table par clé — `kind`, `strict`,
  `solo`, `squad`, `regulated` — reproduisant la table de BHV-3.
- **`lab/engine/run_settings.json`** : `{"permissions": {"deny": ["Edit(**/.approvals/**)", "Edit(**/.runs/**)"]}}` — aucun hook.
- **`lab/plugin/.claude-plugin/plugin.json`** : `name = "fde-kit"`, `version` = version du paquet.
- **`.claude-plugin/marketplace.json`** (racine du repo) : une entrée `fde-kit`, source `./lab/plugin`.
- **CLI** : `lab init <project> --profile <solo|squad|regulated> [--dry-run]` ; `lab run <feature> [--project p] [options d'orchestrate]` ;
  `lab validate <feature> [--project p]` ; `lab policy [--project p]` ; `lab version`.
  Itération 3 : `lab next <feature> [--project p]` (ADR-17) ; `lab spec-lint <feature>` et
  `lab design-lint <feature>` (ADR-19) ; `lab goldfish <feature> [--project p]` (ADR-24).
- **Fin de réponse de l'implementer** (ADR-20) : `STATUS: done` | `STATUS: blocked — <OQ|ADR|scope>: <raison>`.
- **`.runs/state.json`** (ADR-18, gitignoré) :
  ```json
  {"schema_version": 2,
   "tasks": {"T1": "done", "T3": "pending"},
   "reopened": ["T3"],
   "rejections": {"CP-1": 1},
   "routes": {"T4": {"R2": 1}}}
  ```
  Un fichier sans `schema_version` est l'ancien format plat, relu comme `tasks`.
- **Propositions** (ADR-21, versionnées) : `.runs/<Tn>-<Rn>-<sujet>.md` ; décision par
  `approve.sh <Tn>-<Rn> <feature>` / `reject.sh <Tn>-<Rn> <feature> "raison"`.
- **OQ d'agent** (ADR-22, versionnée) : `.runs/<Tn>-OQ.md`, écrite par le moteur.

## 6. Design System & Global Ready

Sans objet (outillage en ligne de commande, pas d'interface).

## 7. Observability & rollout

- Journal de run inchangé en itération 1. Itération 2 : l'événement `run_start` porte le profil et
  la politique effective (clé, valeur, origine) — un run se relit avec ses réglages.
- **Rollout** : tag `v0.1.0` du kit ; vérification sur les deux exemples (`lab init` puis
  `lab run --project examples/<x> --dry-run`) avant la campagne live d'ADR-11 ; aucune mission
  réelle avant cette campagne.
- **Rollout itération 2** : version du kit `0.2.0` (les exemples ré-épinglent explicitement, INV-7) ;
  `lab policy` vérifié sur les deux exemples et sur le kit ; un run `regulated` sur une instance
  externe en sandbox Docker réelle avant le tag.
- **Rollout itération 3** : version du kit `0.3.0`. Avant le tag : design-lint passé sur les designs
  existants (ADR-19) ; campagne facturée de re-mesure après le changement de grammaire `STATUS:`
  (ADR-20) et campagne du rôle `goldfish` (ADR-24), chacune en smoke d'abord avec l'accord de
  l'Owner ; journal : un événement par route empruntée (route, tâche, mode, budget restant) —
  matière du KPI « interventions humaines » et de la décision sur le test goldfish (spec §1).

## 8. Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `--bare` devient le défaut de `-p` et ignore les hooks du plugin | M | M | Aucun garde-fou de run ne dépend d'un hook (ADR-2) ; denies via `--settings` (l'aide locale indique que `--settings` s'applique en `--bare`, à confirmer par la campagne live) |
| Le changement de canal des règles dégrade la chaîne de commandement | M | H | Campagne live ADR-11 avant toute mission ; un échec chain est éliminatoire |
| Migration `examples/` : régression silencieuse (content_guard aveugle aux fichiers déplacés) | M | M | `git mv` pur, `just gate-ci` + `examples-gate` verts, relu au checkpoint |
| Écriture sous `.approvals/` par sous-processus | L | H | Modèle de confiance existant : approbations signées (HMAC) + sandbox comme frontière dure |
| Divergence version paquet / plugin / marketplace | L | M | Test de cohérence (I-19) dans le gate |
| CLI Claude Code trop ancienne chez le FDE | M | M | Pré-vol `claude --version` ≥ 2.1.295 (ADR-6) |
| `.lab/lab.toml` exigé partout (ADR-16) casse les bacs à sable de test et les runs existants | H | M | Les fixtures écrivent le fichier ; message de pré-vol qui nomme la commande `lab init … --profile` |
| Docker indisponible là où l'on développe : ADR-15 non vérifié en réel | M | H | Tests d'argv sans Docker dans le gate ; essai Docker réel exigé au checkpoint avant le tag |
| Un override de route accepté en itération 2 mais sans effet trompe l'Owner | M | L | `lab policy` affiche « appliqué à partir de l'itération 3 » à côté de chaque route |
| La nouvelle grammaire `STATUS:` n'est pas suivie par un modèle : tout blocage part en `human` | M | M | BHV-5c rend l'erreur sûre (jamais `auto`) ; campagne de re-mesure avant le tag (ADR-20) |
| Perte de l'environnement : compteurs de rejets et budgets de route remis à zéro | M | M | Tâches `done` reconstruites depuis git (ADR-18) ; remise à zéro affichée par le moteur |
| Le reset ciblé laisse `done` un dépendant réellement cassé | M | M | Filet BHV-6b : eval globale au checkpoint suivant, puis R6/R7 |
| Isolement goldfish incomplet (plugin ou `CLAUDE.md` de niveau utilisateur) | L | H | `--safe-mode` + `--tools ""` + répertoire hors git, vérifiés par smokes (rapport design-scout) ; marqueurs par source à chaque test : test invalide plutôt qu'un score faux (BHV-8b) |
| Une version de la CLI change le comportement de `--safe-mode` | M | H | Les marqueurs sont tirés à chaque test : une fuite rend le test invalide (rc 1), jamais un score |
| Le design-lint rejette des designs existants | H | L | Passage sur les designs existants avant l'activation ; correction par amendement (ADR-19) |

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-11-12 | Owner + design-scout | Design de l'itération 1 (kit portable) : ADR-1..11, dont 4 décisions Owner par QCM (plugin explicite en run, `lab/plugin` source unique, exemples en instances autonomes, sandbox + instance refusée) |
| 0.2.0 | 2026-11-12 | FDE | Design validé : ADR-1..11 acceptés, emplacement `lab/plugin/` confirmé |
| 0.3.0 | 2026-11-12 | FDE | Trous relevés par le planner tranchés : status line dans le plugin câblée par le FDE (OQ-9, ADR-3), modèles `work/_templates/*.template.md` (OQ-10, ADR-7), `--profile` obligatoire et exemples en `squad` (OQ-11, ADR-7/9) ; message d'ADR-6 aligné sur EX-5 |
| 0.4.0 | 2026-11-12 | FDE | ADR-12 (proposed) : spike promptfoo pour le banc d'évaluation, à mener dans l'itération multi-outils ; pointeur spec 0.6.0 |
| 0.6.0 | 2026-11-13 | Owner | INV-5 garanti aussi à l'exécution (ADR-14) : un CP final/merge n'est jamais auto-validé, même sous `--force` — trou relevé par la revue CP-7 et corrigé par T18 |
| 0.7.0 | 2026-11-14 | Owner + design-scout (brouillon) | Itération 3 (workflow de bout en bout) : ADR-17 `lab next`, ADR-18 état de run git + `state.json`, ADR-19 spec-lint / design-lint, ADR-20 classifieur et `STATUS:` structuré, ADR-21 propositions signées, ADR-22 OQ par le moteur + INV-10 complet, ADR-23 reset ciblé, ADR-24 test goldfish ; patterns I-26..I-45, références E-18..E-21 ; 6 décisions Owner par QCM. **Brouillon : à valider** |
| 0.7.1 | 2026-11-14 | Owner (QCM) | Points ouverts de 0.7.0 tranchés : PyYAML pour les EX (§3, ADR-24), BHV-4 amendé en spec 0.9.0 (ADR-18), isolement goldfish par `--safe-mode` + `--tools ""` + répertoire hors git, marqueurs par source (ADR-24, BHV-8b de la spec 0.9.0). **Brouillon : à valider** |
| 0.5.0 | 2026-11-12 | Owner | Itération 2 (profils) : ADR-13 politique effective (plancher monotone ⊕ overrides, profils en données), ADR-14 un point d'application par clé, ADR-15 sandbox d'instance externe (kit monté en lecture seule, remplace ADR-10), ADR-16 le kit est une instance de lui-même. 3 décisions Owner par QCM : routes réservées dès l'itération 2, sandbox externe livrée, `.lab/lab.toml` du kit explicite |

## 10. Points ouverts de l'amendement 0.7.0 — tranchés le 2026-11-14 (0.7.1)

Tranchés par l'Owner par QCM, sur les faits de la section « Vérifications » du rapport
`work/fde-kit/.runs/design-scout-iteration-3.md`.

1. **Lecture des EX en YAML** → PyYAML, seule dépendance d'exécution (§3, ADR-24). Faits : 28 blocs EX
   dans 10 specs utilisent mappings et séquences en bloc et en flux, scalaires `|`, documents `---`,
   commentaires, guillemets.
2. **BHV-4 et git** → amendement de spec 0.9.0 : BHV-4 nomme l'historique git (ADR-18).
3. **Isolement goldfish** → `--safe-mode` + `--tools ""` + répertoire hors de tout dépôt, marqueurs
   pour les règles dures (hook d'un plugin leurre) et `CLAUDE.md`, vérification « hors dépôt » pour
   git (ADR-24) ; BHV-8b amendé en spec 0.9.0. Faits : smokes facturés (5 appels Haiku 5.5, 0,0032 $).
