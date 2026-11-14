# Progress — passation de session (mise à jour 2026-11-14, fin de session 5)

> **Point d'entrée unique pour reprendre le travail dans une nouvelle session ou un autre compte.**
> `main` = `5df3a60` : lab-fixes (PR #3) puis les PR #4 à #11, mergées le 2026-11-14 sur demande
> de l'Owner (`just gate-ci` rc 0 sur `main` mergé, WSL). Une nouvelle session repart de
> `main` (`git fetch origin && git switch main`), sous **WSL Ubuntu** (§0).
>
> Ordre de lecture : ce fichier en entier → `lab/plugin/rules/hard-rules.md` (la méthode) →
> `work/lab-fixes/{spec,design,tasks}.md` (feature en cours) → `work/fde-kit/{spec,design,tasks}.md`
> (feature mère) → `git log --format='%h %s%n%b' 54fecfc..HEAD` (le **pourquoi** de chaque décision
> est dans les messages de commit).

## 0. TL;DR — où on en est, quoi faire ensuite

| Chantier | État | Référence |
|---|---|---|
| fde-kit itération 1 (kit portable) | ✅ mergée | PR #1 → `b64b227` |
| fde-kit itération 2 (profils solo/squad/regulated, kit 0.2.0) | ✅ mergée | PR #2 → `54fecfc` |
| `reviewer.md` 1.2.0 (verdict sur écarts établis seulement) | ✅ mergé avec la PR #2 | `8479c4c` |
| **`work/lab-fixes`** (lot de correctifs 5, 16, 18, 21, 22, 28, 29, 31) | ✅ mergée (CP-2 signé par l'Owner après 2 rejets : T3, T2) | PR #3 → `5b8d424`, §10.6 |
| Modèles 5.5 seulement (4.x retirés, panel Opus 5.5 ×2) | ✅ PR #4 mergée le 2026-11-14 | `models-latest-only`, §10.7 |
| Item 40 (course résiduelle à l'interruption) | ✅ PR #5 mergée le 2026-11-14 | `fix-interrupt-race`, §10.7 |
| Items 1 + 46 (plan-lint : changelog ignoré, IDs entiers) | ✅ PR #6 mergée le 2026-11-14 | `fix-planlint-changelog`, §10.7 |
| Items 7 + 8 (cas de mesure défectueux) | ✅ PR #8 mergée le 2026-11-14 ; **change l'instrument** → re-mesure facturée des deux cas à faire (smoke d'abord, accord Owner) | `fix-eval-instruments`, §10.7 |
| Item 11 (`LAB_ROOT` relatif) | ✅ PR #9 mergée le 2026-11-14 | `fix-lab-root-relative`, §10.7 |
| Item 12 (rapports de revue dans les commits de tâche) | ✅ PR #10 mergée le 2026-11-14 | `fix-commit-scope-feature-dir`, §10.7 |
| Item 3 (couverture EVAL suite entière) | ✅ PR #11 mergée le 2026-11-14 | `fix-eval-coverage-scope`, §10.7 |
| Items 2, 6, 10, 23–26 | revus en session 5 : chacun demande une décision Owner (preuves et options écrites en §8) | §8 |
| Dépôt `portable` (Claudo-portable) : retrait Windows + modèles 5.5 | ✅ branches `drop-windows` et `models-latest-only` poussées le 2026-11-14 sur demande de l'Owner (aucune PR ouverte, rien de mergé) | §10.7 |
| fde-kit itération 3 | rapport design-scout fait, 6 questions tranchées par l'Owner le 2026-11-14 ; ✅ **design 0.8.0 validé** le 2026-11-14 (ADR-17..24 acceptés) + **spec 0.9.0** approuvée (BHV-4 : git ; BHV-8b : preuve par source), PR #13 mergée ; **plan de l'itération 3 proposé** (`tasks.md` 0.3.0, T23–T35, CP-8..CP-11, plan-lint rc 0), branche `plan-iter3` — **approbation de l'Owner attendue** (modes des CP, OQ-13, OQ-14) | `work/fde-kit/.runs/design-scout-iteration-3.md`, §11 |

**Prochaine action (Owner) :** approuver le plan de l'itération 3 (`work/fde-kit/tasks.md` 0.3.0,
branche `plan-iter3`) : modes des checkpoints CP-8..CP-11 et réponses à OQ-13 / OQ-14 ; ensuite,
exécution par l'orchestrateur sous WSL (`lab run work/fde-kit`), checkpoints signés par l'Owner. Ensuite : plan de l'itération 3 (planner) ; re-mesure facturée des deux
cas de la PR #8 (smoke d'abord).

**Environnement depuis la session 4 : WSL Ubuntu uniquement** (décision Owner). Le moteur exige
POSIX (`import fcntl`, groupes de process) : `just gate-ci` échoue en Windows natif. Clone de travail :
`~/work/lab-fixes` sous WSL ; `claude` CLI installé et authentifié dans WSL.

**Actions Owner hors session (la session cloud ne peut pas les faire) :**
1. Créer les tags `v0.1.0` sur `b64b227` et `v0.2.0` sur `54fecfc` (push de tag refusé en 403 depuis la session).
2. Avant de considérer `v0.2.0` comme prouvé : un run `regulated` réel en bac à sable Docker sur une
   machine avec un démon Docker (`docs/how-to/use-the-sandbox.md`) — seule preuve réelle d'ADR-15.
   La session cloud n'a pas de démon Docker.

## 1. Objectif

Faire du lab un **kit FDE portable** : un SDLC agentique qu'un FDE apporte sur chaque nouvelle
mission, adaptable au niveau d'organisation, avec des retours arrière automatiques quand un
agent n'atteint pas son objectif, et une amélioration continue gouvernée. Feature mère :
`work/fde-kit/`.

Consigne de l'Owner pour ces sessions : **on teste tout le processus pour améliorer le produit.**
Chaque blocage d'un run devient un garde-fou du moteur (`lab/engine/`) et une entrée du lot de
correctifs (§8). Le kit s'améliore en se faisant tourner sur lui-même.

## 2. Où en sont les artefacts

| Artefact | Version | Statut |
|---|---|---|
| `work/fde-kit/spec.md` | 0.8.0 | validated |
| `work/fde-kit/design.md` | 0.6.0 | validated |
| `work/fde-kit/tasks.md` | 0.2.0 | approved (itérations 1 et 2 terminées) |
| `work/lab-fixes/spec.md` | 0.3.0 | validated |
| `work/lab-fixes/design.md` | 0.1.0 | validated (ADR-1..7), pointeur spec 0.3.0 |
| `work/lab-fixes/tasks.md` | 0.1.0 | approved ; T1–T6, CP-1, CP-2 faits (CP-2 signé 2026-11-13) |
| `lab/plugin/agents/reviewer.md` | 1.2.0 | — |
| `lab/models/registry.toml` | — | rôles Claude 5 (voir §4) |
| Kit | 0.2.0 | `examples/` ré-épinglés |

**Itérations prévues** (spec fde-kit) : 1 kit portable ✅ · 2 profils solo/squad/regulated ✅ ·
3 workflow de bout en bout, retours arrière R1–R7, test goldfish à deux lecteurs · 4 retro +
rôle `improver` (auto-amélioration gouvernée) · multi-outils (Copilot, opencode, Codex CLI ;
spike promptfoo, ADR-12).

## 3. Décisions de l'Owner (toutes prises par QCM, détail dans les commits)

- **Distribution** : 100 % plugin Claude Code côté FDE (`lab/plugin/`) ; rien d'outillage agent
  dans le repo client (INV-8) ; « mode instance » plus tard (NG-6).
- **Ce repo = le kit** ; démos `devis` et `booking` → `examples/` en instances autonomes.
- **Profils** `solo` / `squad` / `regulated` ; `--profile` obligatoire ; exemples en `squad`.
  Itération 2 : routes réservées, bac à sable externe construit, le kit a son propre `.lab/lab.toml`.
- **Retours arrière** : plan delta toujours humain ; OQ d'agent → `.runs/` (écrit par le moteur) ;
  reset ciblé des dépendants ; retros locales au FDE ; KPI mesuré d'abord.
- **Goldfish** (emprunté au pattern Elephant/Goldfish, pas le plugin) : test mesurable, deux
  lecteurs (Haiku + modèle de l'implementer), mesure seule, gardé seulement s'il réduit R3/R4.
- **Multi-outils** : Copilot, opencode, Codex CLI ; interactif d'abord ; nouvelle itération ;
  outil qui ne lit ses règles que dans le repo → attend le mode instance.
- **promptfoo** : pas utilisé aujourd'hui (le harnais d'evals est `pytest -m eval` + `eval_models.py`) ;
  spike dans l'itération multi-outils (ADR-12), adoption sur preuve.
- **Improver** : itération 4 (BHV-12, INV-16) — propose, jamais n'applique.
- **lab-fixes** : OQ-1 → abandon de l'ensemble fermé `{sdlc-rework, fde-kit}` dans
  `test_eval_8_examples.py` (on vérifie qu'aucune démo n'est suivie sous `work/`) ; OQ-2 → les deux
  tests qui stubbaient `subprocess.run` passent sur `run_tracked` ; OQ-3 → **l'Owner re-signe** une
  tâche voie Owner interrompue entre signature et contrôles (BHV-1c).

### Règles de signature (important pour la session suivante)

- Les checkpoints et les tâches voie Owner se signent avec `lab/engine/approve.sh <CP> work/<f>`
  (jeton HMAC) ou se rejettent avec `lab/engine/reject.sh <CP> work/<f> "raison" [Tn …]`.
- **L'assistant ne signe que sur une instruction explicite de l'Owner** : « approve CP-n » ou
  « reject CP-n: raison ». Un « Go » nu ne suffit pas (refusé par le classifieur de sécurité ; c'est
  voulu). L'autorisation « fais tous les approves » donnée pendant la session 2 valait **pour cette
  session seulement** — elle ne se transmet pas.
- Ne jamais éditer un plan approuvé, une spec ou un design validés sans le feu vert de l'Owner :
  une OQ d'agent devient un **amendement Owner** (commit séparé, bump de version, passe de
  cohérence des pointeurs `version :` dans design/tasks).
- Un rejet de checkpoint est limité à 2 par checkpoint : un rejet doit prescrire le **besoin**, pas
  un mécanisme.

## 4. Modèles

`[roles]` : implementer `claude-sonnet-5-5`, planner + reviewer `claude-opus-5-5`,
eval-runner `claude-haiku-5-5`. Campagne du 2026-11-12 (17,14 $) + campagne CP-4 (3 modèles de
prod, 3,77 $ : chaîne 9/9, behavioral 8/11 chacun). Preuve = non-régression (n=1 par golden).
Scorecards : `lab/models/scorecards/2026-11-12-*.md|jsonl`.
Les panels de revue mélangent les modèles (ex. CP-2 : `claude-opus-5-5` + `claude-opus-4-8`).
La revue goldfish n'a pas encore été lancée (itération 3) : Haiku n'a donc pas encore servi de lecteur goldfish.

`just eval-models` prend des **paramètres positionnels** : `just eval-models <layer> <live> <models>`,
par ex. `just eval-models behavioral 1 claude-sonnet-5-5`. La forme `layer=… live=1` ne lance rien
(`just` la passe telle quelle) — corrigé dans les docs par lab-fixes T6 et verrouillé par EVAL-7.
Depuis lab-fixes T5, chaque couche écrit `lab/models/scorecards/<YYYY-MM-DD>-<layer>.md|jsonl`
(suffixe `-2`, `-3`… si le fichier existe), plus de `latest`.

## 5. Itération 1 (kit portable) — terminée, mergée (PR #1 → `b64b227`)

Session 2 : rejeu complet demandé par l'Owner (le `state.json` n'avait pas survécu au changement de
session). T1–T10 rejoués (commits « journal seul », `15f628c`…`0b09785`), puis :

| Nœud | État | Commit(s) |
|---|---|---|
| T1–T10, CP-1, CP-2 | ✅ (rejeu) | réel : `efcc57d`…`a44e003` ; rejeu : `15f628c`…`0b09785` |
| T7 | ✅ débloqué par le delta de plan `e86d8c4` | `d7b434a` |
| T9 | ✅ après **rejet CP-3** (test hors scope → delta `314bf39`) | `e8da4a2` + `cda972e` |
| CP-3 | ✅ | `1f183f0` |
| T15 | ✅ **voie Owner** (fichiers protégés `.claude/` → `lab/plugin/`) | `f93438a` (+ `2be6b62`) |
| T11 | ✅ (scindé après blocage chemins protégés) | `50f9c61` |
| T12, T13 | ✅ ; T13 retravaillé après **2 rejets CP-4** | `a243a5d`, `ac9aed9` |
| CP-4 | ✅ campagne ADR-11 | `0b32947` |
| T14 | ✅ après **rejet CP-5** (ruff format) | `10293ef` + `e72d97e` |
| CP-5 | ✅ → PR #1 ; CI rouge corrigée (`1dbfd26`, lint de capacité lu depuis git) | `b5579d9` |

Contrôles live CP-4 : **EX-5 ✅** (un `claude -p` avec l'argv du run ne peut pas écrire
`.approvals/CP-1` — hook `guard_paths`) ; **BHV-2b ✅** (une session `--plugin-dir lab/plugin` reçoit
les 8 règles via SessionStart) ; `--settings` sous `--bare` : non concluant (le moteur ne passe
jamais `--bare`).

## 6. Garde-fous ajoutés au moteur pendant les runs (hors plan, Owner)

| Commit | Amélioration | Déclencheur |
|---|---|---|
| `f4f151c` | **Scope leak** : une tâche verte grâce à des fichiers hors `files_touched` est renvoyée à l'agent | CP-3 BLOCK (T9) |
| `ed61c07` | **Voie Owner** (`**agent:** owner`) + **lint de capacité** (tâche agent sur chemin protégé = erreur ; prompt demandant `git mv`/`git rm`/`just` = warning) | T11 bloqué |
| `1dbfd26` | Lint de capacité : tâches « done » dérivées de l'historique git, pas de `state.json` (gitignoré) | CI rouge PR #1 |
| `94f273e` | Trajectory guard : `owner_signed` journalisé = preuve d'une tâche Owner | revue CP-4 |
| `2f3fe92` | Le `Why:` d'un commit auto de rework cite le rejet de checkpoint | revue CP-4 |
| `4bf2b48` | Essais de modèles : fichier de rôle copié dans le cwd de l'essai (plus d'`--add-dir` vers le kit qui exposait les clés de réponse) | revue CP-4 |
| `876a54d` | `just lint-check` du projet fait partie du gate de tâche | CP-5 BLOCK (T14) |
| `5a70c84` | `guard_paths.sh` lit aussi `notebook_path` | revue CP-5 |
| `deffc82` | Un rejet en attente est honoré avant de payer un panel de revue | redémarrage à CP-5 |
| `3c5b3a5` | Trajectory guard : seulement les commits `Run: auto` ; jeton signé archivé = preuve Owner | revue CP-5 |
| `a2a282c` | Vague parallèle : chaque tâche jugée sur un arbre stabilisé ; le périmètre de chaque sœur vaut toute la vague | itération 2 |
| `369bdec` | Aucune tâche n'édite pendant qu'une sœur se fait juger (tâches en file) | revue CP-7 |
| lab-fixes T1–T3 | Arrêt propre (SIGINT/SIGTERM), dry-run muet, trailers exacts, source du budget, gate non mutant, tampons de scorecard datés | §10 |

Leçons : une tâche scindée doit rester verte à chaque étape ; un rejet prescrit le **besoin**, pas
le mécanisme ; aucun contrôle de gate ne doit dépendre d'un état hors git ; un commit ne part que si
le pre-commit passe (`bash .githooks/pre-commit && git commit …`) ; ne citer que des hashes vérifiés.

## 7. Itération 2 (profils d'organisation) — terminée, mergée (PR #2 → `54fecfc`)

Spec **0.8.0**, design **0.6.0**, tasks **0.2.0** ; 29 nœuds ✅ ; kit **0.2.0** (exemples
ré-épinglés). Coût agents ≈ 5,3 $ (dernier run). Code : `lab/engine/policy.py`,
`policy_profiles.toml`, `planlint.py`, `sandbox_runner.py`, `cli.py` (`lab policy`) ;
`.lab/lab.toml` obligatoire ; INV-5 appliqué au plan-lint **et** à l'exécution (design 0.6.0).
Checkpoints, tous signés par l'Owner : CP-6 (rejeté une fois → T16, spec 0.7.0 BHV-3d), CP-7
(rejeté une fois → T18 + T16 budget fini, spec 0.8.0).

## 8. Lot de correctifs du lab (hors plan)

Faits : 4 (`2b8f327`), 9 (`5a70c84`), 13 (`ed61c07`), 14 (`f4f151c`), 17 (`2f3fe92`), 27 (`1dbfd26`),
30 (`2cf51a8`), 32 (`a2a282c`, `369bdec`) ; **5, 16, 18, 21, 22, 28, 29, 31 par la feature
`lab-fixes`** (en attente du merge CP-2).

1. ✅ PR #6 (mergée le 2026-11-14) (`1144cb6`) — plan-lint : la vérif d'existence d'un ID de spec matche aussi les IDs supprimés cités dans le changelog.
2. `work/sdlc-rework/tasks.md` : 17 erreurs plan-lint ; plan-lint seulement informatif en CI. Revu en session 5 : les 17 sont de vrais chevauchements de tâches parallèles (`justfile`, `tests/sdlc_rework/`) dans le plan **approuvé** d'une feature livrée (PR #33) → le corriger = éditer un plan approuvé : **décision Owner** (corriger l'historique, ou le laisser et exclure la feature du lint).
3. ✅ PR #11 (mergée le 2026-11-14) (`0876b6f`) — Couverture d'evals (`eval_covers`) cherchée dans toute la suite, pas par feature. Correctif proposé : seule compte une eval dont le fichier est dans le `files_touched` de la tâche ; les trois tests qui fixaient l'ancien comportement listent maintenant leur fichier d'eval (assertions inchangées, verts aussi sur l'ancien code). **Revu en session 5, preuve que le trou est réel** : aucun test de `tests/sdlc_rework/` ne suit le nommage `test_eval_n_*`, et pourtant les 7 tâches EVAL de `sdlc-rework` ont passé le contrôle — couvertes par les `test_eval_1_…` d'autres features. Dans les features conformes, 22 paires tâche/EVAL sur 22 ont leur test dans le `files_touched` de la tâche. **Décision Owner** : borner la couverture au `files_touched` de la tâche contredit trois tests qui fixent volontairement le comportement actuel (`tests/orchestrator/test_orchestrate.py:322`, `:416`, `:436` — ce dernier dit « NO engine change » pour le seam JS) ; borner par dossier de tests de la feature suppose une correspondance feature → dossier qui n'est définie nulle part. Options : (a) bornage `files_touched` + réécriture de ces trois tests, (b) correspondance feature → dossier à définir, (c) statu quo documenté.
4. ✅ (`2b8f327`)
5. ✅ lab-fixes T3 — `--dry-run` n'écrit plus rien sous `.runs/` (BHV-2, EVAL-2).
6. `eval_models.py` compte une erreur d'API comme un échec. Revu en session 5 : aucun contrat écrit (code, EVOLUTION.md, how-to) ne dit quoi faire d'une erreur ; chaque option change la notation et la comparabilité des campagnes, et la couche chain est éliminatoire → **décision Owner** : (a) exclure l'essai du dénominateur et le compter à part, (b) le rejouer N fois, (c) statut `error` distinct qui bloque la recommandation de rôle. `call_model` ne distingue aujourd'hui ni erreur d'API, ni timeout, ni max-turns (`ok = returncode == 0`).
7. ✅ PR #8 (mergée le 2026-11-14) (`c3a0fbb`) — Cas `BEH-eval-correct` : demande un fichier hors `files_touched`. Le cas a maintenant son propre tasks.md (les deux fichiers) + garde `tests/golden/test_case_scope.py`. Change l'instrument de mesure : merge par l'Owner, puis run behavioral **facturé** pour mesurer.
8. ✅ PR #8 (mergée le 2026-11-14) (`11be242`) — Golden `remise-paliers` échoue pour 5 modèles sur 6. **Cause trouvée** : l'oracle exige `is_estimate is True` alors que la spec saute de INV-1 à INV-3 (l'INV-2 de `devis-calc` manque) ; prouvé hors ligne (implémentation fidèle à la spec avec `False` → logic FAIL, avec `True` → logic OK). INV-2 rétabli + garde `tests/golden/test_spec_oracle_rules.py`. Change l'instrument : merge Owner, puis run scorecard **facturé**. Non expliqué : l'échec `scorecard-api` (`No module named 'compute'`) de 5 modèles — les répertoires d'essai sont supprimés, il faut un run pour l'observer.
9. ✅ `guard_paths.sh` lit `notebook_path` (`5a70c84`).
10. Pré-vol : compare la version du kit, pas celle de `plugin.json` (à trancher : texte BHV-2a vs ADR-2) — **décision Owner** (laquelle des deux sources fait foi).
11. ✅ PR #9 (mergée le 2026-11-14) (`2626a89`) — `LAB_ROOT` relatif + `--project` sur le même dossier : `kit_root()` résout maintenant `LAB_ROOT` (comparé à un `PROJECT` résolu).
12. ✅ PR #10 (mergée le 2026-11-14) (`78638cb`) — `scoped_commit` stage tout le dossier de la feature (rapports de revue embarqués dans les commits de tâche — encore vu sur T6 de lab-fixes, qui embarque `CP-1-review.md`).
13. ✅ (`ed61c07`)
14. ✅ (`f4f151c`)
15. Le reviewer ne peut lancer ni `just` ni `git` (approbation demandée) : les revues CP retombent sur la lecture de code ou `pytest`/`ruff` directs. → voie Owner / allowlist reviewer. — Vérifié en session 5 : le tour du reviewer reçoit les mêmes `ALLOWED_TOOLS` que l'implementer (`runner.DEFAULT_ALLOWED_TOOLS` : `uv`, `make`, `python3`, `mkdir`, `ls`, `git diff`, `git log` — ni `just`, ni `git show`) ; `Bash(just:*)` ouvrirait toutes les recettes, y compris les mutantes (`lint`) → liste par recette ou par rôle à décider : **Owner** (sécurité).
16. ✅ lab-fixes T3 — `Artifacts:` = chemins réellement stagés, triés (BHV-3, EVAL-3). Voir 35 (renommages).
17. ✅ (`2f3fe92`)
18. ✅ lab-fixes T6 — docs `just eval-models` en positionnel, verrouillé par EVAL-7.
19. Isolation des essais de modèles : `--plugin-dir`/`--settings` restent des chemins du kit dans l'argv ; confinement complet = bac à sable OS (candidat ADR). — Vérifié en session 5 : ADR-2 (design fde-kit, « accepted, décision Owner : `--plugin-dir` explicite ») fixe ces chemins dans l'argv ; un confinement OS est un nouvel ADR → **Owner**.
20. Un rejet de checkpoint consomme vite le budget (max 2) quand c'est la **prescription** du rejet qui est fausse : prévoir un « amendement de note de rejet » ou un rejet qui ne compte pas. — Vérifié en session 5 : `max_cp_rejects = 2` est dans la spec fde-kit validée (tableau des profils l. 170, route R7 l. 213) → amendement de spec : **Owner**.
21. ✅ lab-fixes T5 — tampons `<date>-<layer>` (+ `-2`…), plus d'écrasement (BHV-6, EVAL-6).
22. ✅ lab-fixes T4 — `gate: lint-check test evals check-brand check-lock` (BHV-4, EVAL-4).
23. `eval_gate.sh` : filtre d'extensions (`.py|.toml|.ts…`) — une instance non-Python n'est pas gardée en fin de session. **Décision Owner** : élargir le déclencheur fait payer les evals sur plus de tours et demande de choisir ce qui compte comme du code (liste par langage, ou « tout sauf `*.md` »). Le design fde-kit dit que ce hook est « un plus » à côté du gate du moteur.
24. `lab init` pas atomique : seul le justfile est restauré en cas d'échec (conforme ADR-8, mais surprenant) — le changer = amender ADR-8 : **décision Owner**.
25. `46ab6dc` porte un tag `[BHV-7]` parasite (périmètre itération 4) — le corriger = réécrire l'historique (NG-4) : à clore sans correctif si l'Owner l'accepte.
26. `brand_denylist.txt` vide : `check-brand` passe à vide (voulu ? à confirmer avant la première mission) — **décision Owner** : seul l'Owner connaît les noms à interdire.
27. ✅ (`1dbfd26`) — règle : aucun contrôle de gate ne dépend d'un état hors git.
28. ✅ lab-fixes T1+T2 — SIGINT/SIGTERM : drapeau STOP, workers drainés, aucun commit, groupes de process tués, tâches en vol → `pending`, `run_interrupted`, rc 130 (BHV-1, EVAL-1).
29. ✅ lab-fixes T6 — même cause que 18 (prompt « corrige partout » = invitation à la fuite de périmètre : leçon de planification).
30. ✅ (`2cf51a8`)
31. ✅ lab-fixes T3 — le message de budget nomme sa source (`LAB_BUDGET_USD` ou `budget_usd, <origine>`) (BHV-5, EVAL-5).
32. ✅ (`a2a282c`, `369bdec`)
33. Ne jamais manipuler `git stash` pendant que le travail d'une tâche y est mis de côté. — Vérifié en session 5 : aucune règle `stash` dans `lab/plugin/rules/hard-rules.md`, `CLAUDE.md` ni les agents ; l'y inscrire change la méthode → **Owner**.

**Nouveaux, relevés pendant le run lab-fixes (session 3) :**

34. Au premier run lab-fixes, des agents ont **écrit leurs OQ directement dans `spec.md`** (artefact validé). Converties en amendements Owner (spec 0.2.0, 0.3.0). La décision « OQ d'agent → `.runs/`, écrit par le moteur » (itération 3) doit l'empêcher mécaniquement.
35. **Renommage absent du trailer `Artifacts:`** (revue CP-2, panéliste 1) : `git diff --cached --name-only` a la détection de renommage active ; un `a → b` stagé ne liste que `b`. Correctif : `--no-renames` dans `scoped_commit` (`lab/engine/orchestrate.py` ~l. 605) + un cas renommage dans EVAL-3. Écart à INV-3 « ni plus ni moins ». **C'est la décision ouverte de CP-2 (§10.4).**
36. Amorçage des trailers : les commits qui livrent un correctif du moteur sont faits par l'ancien moteur (T1–T6 de lab-fixes ont des `Artifacts:` incomplets). Documenté, protégé par NG-4 — à garder en tête pour toute feature qui modifie le moteur qui l'exécute.
37. Redémarrer l'orchestrateur à un checkpoint **re-paie le panel de revue** même si seule la signature manque (voulu : « une approbation n'est jamais court-circuitée »). Coût ≈ 1–3 $ par redémarrage. Piste : réutiliser un rapport dont le HEAD n'a pas bougé. — Vérifié en session 5 : le moteur l'interdit explicitement (`orchestrate.py:1125-1126` : « An approval is never short-cut — the review is regenerated first (self-hosting protocol) »), alors que le dépôt `portable` a déjà une réutilisation (`50783e7` : rapport réutilisé tant que l'**arbre** relu ne change pas ; `b9b96c7` : jetons signés liés à un nonce par tour). Les deux lignées divergent → **Owner** : porter ce mécanisme ici, ou garder la règle.
38. **L'état de run est gitignoré** (`.runs/state.json`, `journal.jsonl`, `.approvals/`) : dans une session cloud, il meurt avec le conteneur → un changement de session force un rejeu ou une reconstruction à la main (déjà vu à l'itération 1, revu ici). Piste : dériver l'état « done » de l'historique git comme le lint de capacité (`1dbfd26`), ou un export/import explicite de l'état. — Vérifié en session 5 : la spec fde-kit validée (BHV-4, itération 3) nomme `.runs/state.json` comme source de la phase courante ; dériver l'état de git = amendement de spec, un export/import = nouvelle commande non spécifiée → **Owner** (à trancher avec la conception de l'itération 3).
39. `LAB_APPROVAL_SECRET` vit dans le scratchpad de la session : perdu avec elle. Un nouveau secret fonctionne, mais les jetons signés avec l'ancien deviennent invalides (sans conséquence tant qu'aucun jeton n'est en attente). — Session 5 (WSL) : le secret vit maintenant hors scratchpad, dans `~/.lab-secrets/approval` (mode 600) sur la machine de l'Owner ; il survit aux sessions locales, pas aux sessions cloud.

**Nouveaux, relevés pendant la clôture lab-fixes (session 4) :**

40. ✅ PR #5 (mergée le 2026-11-14) (`c47edb6`) — **Course résiduelle à l'interruption** (revue CP-2 finale, panéliste 1, non reproduite) : un signal entre le dernier `if STOP.is_set()` et `_TRACKED.add(p)` dans `runner.run_tracked` laisse un agent échapper au `terminate_all`. Dans une vague, la boucle à 0,2 s le rattrape ; dans le panel de revue (thread principal), rien ne re-signale et le tour va au bout. Aucun commit possible. Piste : drapeau « terminé » dans `runner`, posé par `terminate_all`/`kill_all_now`, vérifié par `run_tracked` juste après l'enregistrement.
41. `work/lab-fixes/tasks.md:21` : la ligne de couverture ne cite pas `BHV-1c` (oubli de la passe de cohérence spec 0.3.0). Cosmétique.
42. **OQ-4** (différée par l'Owner) : une tâche voie Owner signée mais pas encore vérifiée est listée dans `run_interrupted.inflight` ; le glossaire dit « en vol dès que le jugement commence ». BHV-1c tient dans les deux cas.
43. ✅ PR #10 (mergée le 2026-11-14) — Item 12 revu : le commit T2 (`c9a44e4`) embarque `work/lab-fixes/.runs/CP-2-review.md` (rapport de la revue précédente).
44. ✅ PR #4 (mergée le 2026-11-14) — La revue CP-2 utilisait encore `claude-opus-4-8` comme second panéliste. Décision finale de l'Owner : Haiku 5.5 s'il convient, sinon Opus ; Haiku 5.5 n'est pas éligible relecteur (WARN sur du code propre), Sonnet 5.5 est l'implementer → `[review] panel = Opus 5.5 ×2` dans le registre.
45. Le secret d'approbation a été exposé dans le transcript de session (`pgrep -af` affiche la ligne de commande expansée) : ne jamais exporter un secret dans une commande `bash -lc "… export X=$(…)"` qu'on liste ensuite ; il a été régénéré après la clôture.

**Nouveaux (session 5) :**

46. ✅ PR #6 (mergée le 2026-11-14) (`7bc0312`) — plan-lint : la vérif d'existence était un test de sous-chaîne (`BHV-1` trouvé dans `BHV-10`). Corrigé : comparaison aux IDs entiers.
47. Depuis Windows, `wsl.exe -- bash -lc '…'` perd parfois `$var` et la substitution `$(…)` (vu en session 5 : trailer `Artifacts:` vide, corrigé par `--amend` avant push). Pour tout ce qui n'est pas trivial : écrire un script dans un fichier et lancer `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash /mnt/…/script.sh` ; message de commit via `git commit -F <fichier>`.

## 9. Environnement (session cloud)

- `just` installé via `uv tool install rust-just` (à refaire dans une nouvelle session si absent) ;
  `claude` CLI authentifié (2.1.322 en session 2).
- **Pas de démon Docker** (le bac à sable `regulated` ne peut pas tourner ici).
- **Push de tag refusé (403)** : seule la branche de travail peut être poussée.
- Limite de quota « 5 heures » déjà atteinte une fois : un run peut échouer en bloc.
- Règle : un commit ne part que si le pre-commit passe (`bash .githooks/pre-commit && git commit …`).
- Pour travailler sur le kit avec ses propres garde-fous : `claude --plugin-dir lab/plugin`.

## 10. Feature `work/lab-fixes` (sessions 3–4) — mergée (PR #3 → `5b8d424`)

### 10.1 Contenu

Spec 0.3.0 : BHV-1 (interruption : rc 130, tâches en vol → `pending`, `run_interrupted`), BHV-1a
(second signal = sortie immédiate), BHV-1b (une attente de checkpoint / voie Owner n'est **pas** en
vol), BHV-1c (l'Owner re-signe après une interruption), BHV-2 (dry-run sans trace), BHV-3
(`Artifacts:` = chemins stagés), BHV-4 (`gate` non mutant), BHV-5 (source du budget), BHV-6
(tampons datés), BHV-7 (docs positionnelles) ; INV-1..5 ; EX-1..4 ; EVAL-1..7 (déterministes,
`tests/lab_fixes/`). Design 0.1.0 : ADR-1 lanceur suivi (`runner.run_tracked`, `terminate_all`,
`kill_all_now`, groupes de process), ADR-2 drapeau STOP + drain, ADR-3 journal seulement en run réel,
ADR-4 trailers après staging, ADR-5 `gate` → `lint-check`, ADR-6 source du budget + tampons,
ADR-7 docs + test.

### 10.2 Historique du run (orchestrateur)

| Nœud | Résultat | Commit |
|---|---|---|
| spec 0.1.0 / design 0.1.0 / plan | validés / approuvé par l'Owner | `7fdc8da`, `83799d8`, `ee29b16` |
| 1ᵉʳ run | T1 bloqué OQ-2, T4 et T5 bloqués OQ-1 (agents ont écrit les OQ dans la spec → item 34) | — |
| spec 0.2.0 + cohérence + delta | OQ-1, OQ-2 tranchées par l'Owner | `fd13a0d`, `d637605` |
| T4 | gate non mutant + `test_eval_8_examples.py` | `4052e13` |
| T5 | tampons datés | `211b04a` |
| T1 | `run_tracked` / `terminate_all` | `52015e8` |
| T2 | interruption | `089930d` |
| CP-1 | **rejeté** (attente voie Owner comptée en vol ; re-signature) | revue `f5c11d9` |
| spec 0.3.0 + cohérence + delta | BHV-1b explicite, BHV-1c (OQ-3) | `55ca955`, `ac26b3a` |
| T2 (rework) | `kill_all_now` public, cas voie Owner dans EVAL-1 | `787be0e` |
| CP-1 (2ᵉ revue) | WARN : une tâche en file jamais démarrée pouvait être listée en vol → **approuvé, corrigé dans T3** (delta `f61a47b`) | `9e355a1` |
| T6 | docs positionnelles | `009939b` |
| T3 | dry-run muet, trailers, budget, `not_started` | `ee844aa` |
| CP-2 (revue) | WARN (opus-5-5) + PASS (opus-4-8) | `d10f294` |

Coût agents du feature : **≈ 11,3 $** (somme des `cost_usd` du journal, 4 démarrages de run,
5 panels de revue).

### 10.3 Vérifications faites par la session avant CP-2

- `just gate-ci` vert : 185 tests, 160 evals, exemples 8 + 1063.
- `just check-content work/lab-fixes` et `just check-trajectory work/lab-fixes` : OK.
- `--dry-run` réel : `.runs/journal.jsonl` et `state.json` identiques octet pour octet.
- **Ctrl-C live** sur un vrai run (instance temporaire) : rc 130, 1 process `claude` avant / 0 après,
  aucun nouveau commit, `state.json` revenu à T1 `pending`, `run_interrupted` journalisé avec
  `inflight: ["T1"]`.
- **SIGTERM live à un checkpoint (BHV-1b)** : l'orchestrateur en attente à CP-2 a été arrêté par la
  limite de temps de la tâche de fond (18:05) → `run_interrupted` avec `inflight: []`, CP-2 resté
  `pending`, aucun commit, message de reprise affiché. Aucun orchestrateur ne tourne depuis.
- Non fait : interruption live sous Docker (laissée au run de l'itération 3, design §8).

### 10.4 Décision ouverte : CP-2 (merge)

Rapport complet : `work/lab-fixes/.runs/CP-2-review.md` (versionné).

- **Panéliste 1 (correctness, WARN)** — un vrai écart : un fichier renommé dans une tâche n'apparaît
  que sous son nouveau nom dans `Artifacts:` (rename detection de `git diff --cached --name-only`),
  vérifié par le panéliste dans un dépôt jetable. Correctif proposé : `--no-renames` + cas EVAL-3.
  Note (pas un écart) : course minime entre le dernier contrôle STOP et un lancement d'agent, rattrapée
  en ~0,2 s par les `terminate_all()` répétés ; ce process ne peut jamais committer.
- **Panéliste 2 (conformité, PASS)** — traçabilité, ADR, périmètre conformes ; seule remarque : les
  trailers des commits du feature lui-même sont incomplets (amorçage, item 36, NG-4).

Options pour l'Owner :
1. **« approve CP-2 »** et traiter le renommage plus tard (item 35, petite tâche à part ou dans l'itération 3).
2. **« reject CP-2: Artifacts trailer misses renamed source paths — add --no-renames and an EVAL-3 rename case » [T3]** :
   T3 est rejoué, puis nouvelle revue CP-2 (dernier rejet possible avant la limite de 2).

### 10.5 Comment reprendre CP-2 dans une **nouvelle** session / un autre compte

L'état de run n'est pas versionné (item 38) ; dans la session 3 il valait :

```json
{"T1": "done", "T4": "done", "T5": "done", "T2": "done", "CP-1": "done", "T3": "done", "T6": "done", "CP-2": "pending"}
```

Étapes :
1. `git fetch origin ccr-99c581ba-w0vhys && git checkout ccr-99c581ba-w0vhys` ; `uv sync --locked` ;
   installer `just` si besoin (`uv tool install rust-just`).
2. Recréer `work/lab-fixes/.runs/state.json` avec le JSON ci-dessus (le journal de la session 3 est perdu ;
   ce n'est pas bloquant : lab-fixes n'a aucune tâche voie Owner, donc `check-trajectory` ne s'appuie
   que sur les commits `Run: auto`).
3. Générer un nouveau secret, hors du dépôt, et l'exporter dans le shell qui lance l'orchestrateur **et**
   dans celui qui signe : `export LAB_APPROVAL_SECRET="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"`.
   Ne jamais le committer.
4. Lancer `python3 -u lab/engine/orchestrate.py work/lab-fixes` (le moteur va **re-générer la revue
   CP-2**, ≈ 1–3 $, item 37), puis attendre la décision explicite de l'Owner et lancer
   `bash lab/engine/approve.sh CP-2 work/lab-fixes` ou `bash lab/engine/reject.sh CP-2 work/lab-fixes "raison" T3`.
   - Pour éviter le coût de la revue : l'Owner peut décider de signer CP-2 hors moteur (le run est
     fini à part ce nœud) et de passer directement à la PR — à consigner dans le commit de clôture.
5. Après approbation : commit du journal de run final (`tasks.md`) + mise à jour de ce fichier,
   push, **PR `ccr-99c581ba-w0vhys` → `main`** (pas de template de PR dans le dépôt), surveiller la CI,
   merger **seulement sur demande explicite** de l'Owner.

### 10.6 Session 4 (WSL) — clôture

| Nœud | Résultat | Commit |
|---|---|---|
| CP-2 (1ᵉʳ rejet Owner) | renommage absent du trailer `Artifacts:` → T3 | — |
| T3 (rework, 2 essais) | `--no-renames` + cas renommage dans EVAL-3 | `3c5eb4e` |
| CP-2 (revue) | BLOCK (opus-5-5 : un panéliste démarre après STOP, INV-1) + PASS (opus-4-8) | — |
| CP-2 (2ᵉ rejet Owner) | le panel de revue doit s'arrêter sur STOP → T2 | — |
| T2 (rework) | contrôle `STOP` avant/après chaque tour de relecteur + cas EVAL-1 panel à 2 | `c9a44e4` |
| CP-2 (revue) | WARN + WARN (items 40–42) | — |
| CP-2 | **signé par l'Owner** (« approve CP-2 ») | commit de clôture |

Coût agents session 4 : **6,14 $** (somme `cost_usd` du journal). Vérifié dans WSL après T2 :
`just gate-ci` rc 0 (185 tests, 162 evals, exemples 8 + 1063), `just check-content work/lab-fixes` OK,
`just check-trajectory work/lab-fixes` OK (0 warning).

### 10.7 Session 5 (nuit du 2026-11-13 au 14, WSL, sans l'Owner) — ce qui attend une décision

Consigne de l'Owner : avancer autant que possible sans poser de question et sans rien inventer ;
tout ce qui demande une signature ou un merge est laissé prêt et documenté.

**Mergées le 2026-11-14** sur demande explicite de l'Owner, dans l'ordre #5, #6, #9, #10, #11, #4,
#8, #7 (merge commits, chacune `CLEAN` au moment du merge). `just gate-ci` sur `main` = `5df3a60`
(WSL) : rc 0 — ruff OK, 210 tests + 1 skip, 162 evals, 8, 1063 passed.

| PR / branche | Contenu | Vérifié (WSL) | CI |
|---|---|---|---|
| #4 `models-latest-only` (`0a5dea4`) | Registre : entrées Claude 4 retirées ; `[review] panel = Opus 5.5 ×2` lu par `pick_reviewer_models` ; docs/tests/exemple `eval_models` en 5.5 ; test de garde `tests/test_latest_models_only.py` (aucun fichier vivant ne nomme un ID absent du registre ; historique exempté : scorecards, `work/`, `progress.md`) | `just gate-ci` rc 0, 192 tests, 162 evals | ✅ |
| #5 `fix-interrupt-race` (`c47edb6`) | Item 40 : drapeau `runner._STOPPING` posé sous verrou par `terminate_all`/`kill_all_now` ; `run_tracked` se tue s'il s'enregistre après | rc 0, 188 tests ; le test échoue sans le correctif (timeout 30 s) | ✅ |
| #6 `fix-planlint-changelog` (`1144cb6`, `7bc0312`) | Items 1 et 46 | rc 0, 189 tests ; sortie plan-lint identique sur les 6 features existantes | ✅ |
| #8 `fix-eval-instruments` (`11be242`, `c3a0fbb`) | Items 8 et 7 — **change des cas de référence** : merge Owner puis runs facturés (`just eval-models scorecard 1 …`, `behavioral 1 …`) | rc 0, 191 tests + 1 skip ; chaque garde échoue sans son correctif | ✅ |
| #9 `fix-lab-root-relative` (`2626a89`) | Item 11 | rc 0, 187 tests ; le test échoue sans le correctif | ✅ |
| #10 `fix-commit-scope-feature-dir` (`78638cb`, `2a06cbb`) | Items 12 et 43 + INV-10 : un commit de tâche ne prend plus que `tasks.md` dans le dossier de la feature (ni rapports de revue, ni `spec.md`/`design.md`) | rc 0, 187 tests ; chaque test échoue sans son correctif | ✅ |
| #11 `fix-eval-coverage-scope` (`0876b6f`) | Item 3 : couverture EVAL bornée au `files_touched` de la tâche — **change trois tests** (fichiers ajoutés à `files_touched`, assertions inchangées) | rc 0, 186 tests ; le nouveau test échoue sans le correctif | ✅ |

**Dépôt `portable`** (Claudo-portable, `main` local de `D:\Projets\ai-workflow-gates\_build`) :
deux branches committées dans le clone WSL `~/work/portable` (cloné depuis `_build`, `main` = `5ccdfd1`),
**poussées le 2026-11-14** sur demande explicite de l'Owner (`git push portable`, branches neuves sur
`portable/main` = `5ccdfd1` ; aucune PR ouverte, rien de mergé). Le premier essai de push avait été
refusé par le classifieur de permissions :

- `drop-windows` (`09a4477`) : retire le support Windows natif (branche `msvcrt` d'`oslock`, `oscompat.find_bash`,
  `verify.resolve_python`, recherche `claude.cmd`→`claude.exe`, `lab-ws` + `contained(git_modes=…)`, bascule
  `os() == "windows"` du justfile, `tests/conftest.py`, how-to Windows) ; garde le durcissement neutre (UTF-8,
  clés `/`, LF, `LAB_CLAUDE_CMD`, `LAB_PYTHON`, `PYTHONUTF8`). `just gate-ci` rc 0 : 205 tests (220 − 15 tests
  Windows-only), 1084 evals.
- `models-latest-only` (`cde05e7`) : `[roles]` passe en Claude 5 (entrées 5.5 reprises mot pour mot du travail
  non committé de l'Owner), Claude 4 retiré, même panel et même garde que #4. rc 0 : 227 tests, 1084 evals.
  Ce dépôt n'a pas de scorecard Claude 5 à lui : la preuve citée est la campagne 2026-11-12 de ce dépôt-ci.
  Chevauchement attendu avec le travail non committé de `_build` : `lab/models/registry.toml`.

Commande utilisée (depuis `_build`, jamais vers `origin`) : `cd D:\Projets\ai-workflow-gates\_build && git fetch //wsl.localhost/Ubuntu/home/antoine/work/portable drop-windows:p-drop-windows models-latest-only:p-models-latest-only && git push portable p-drop-windows:drop-windows p-models-latest-only:models-latest-only`.

## 11. Ensuite

1. Décisions Owner : approuver le plan de l'itération 3 (proposé, branche `plan-iter3`) ; trancher les items 2, 6, 10, 15, 19, 20, 23–26, 33, 37, 38 (§8). Fait le 2026-11-14 : merge des PR #4 à #12 ; les 6 questions du rapport design-scout (itération 3) sont tranchées ; push des deux branches `portable`.
2. **fde-kit itération 3** — bloquée à l'étape **design** : la spec 0.8.0 (validée) couvre déjà BHV-4..6 et BHV-8, mais le design 0.6.0 dit que les itérations 3 et 4 « seront conçues à leur tour, par amendement de ce document » ; chaque amendement précédent est venu d'un rapport `design-scout` + décisions Owner par QCM. Prochaine étape : lancer `design-scout` sur BHV-4..6, BHV-8 (avec 37 et 38), puis QCM Owner. **Fait en session 5** : `work/fde-kit/.runs/design-scout-iteration-3.md` — 20 patterns internes I-26..I-45 avec fichier:ligne, anti-patterns (dont I-38 : le prompt implementer fait écrire les OQ dans `spec.md`, cause du lab-fix 34), 6 questions pour l’Owner, **tranchées le 2026-11-14** (section « Décisions Owner » du rapport) ; piste externe : E-18 Temporal, E-19 Airflow, E-20 BIG-bench vérifiées sur page primaire ; P6 (Dagster) et la comparaison YAML non établies. Contenu prévu : workflow de bout en bout, retours arrière R1–R7 (avec reset ciblé des
   dépendants), OQ d'agent écrites par le moteur dans `.runs/` (item 34), test goldfish à deux
   lecteurs (Haiku + modèle de l'implementer), interruption live sous Docker. Candidats à absorber :
   items 15, 20, 37, 38 (12 : PR #10).
3. Itération 4 : retro + rôle `improver` (propose, n'applique jamais).
4. Itération multi-outils : Copilot, opencode, Codex CLI ; spike promptfoo (ADR-12).
5. Reste du lot : 15, 19, 20, 33, 37–39 (itération 3 ou conception), 41, 42 (Owner) ; décisions Owner : 2, 6, 10, 23–26 ; corrigés par PR mergées le 2026-11-14 : 1, 3, 7, 8, 11, 12, 40, 43, 46.
