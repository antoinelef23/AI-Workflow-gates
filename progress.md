# Progress — passation de session (mise à jour 2026-11-13, fin de session 3)

> **Point d'entrée unique pour reprendre le travail dans une nouvelle session ou un autre compte.**
> Branche de travail : **`ccr-99c581ba-w0vhys`** (tout est poussé ; `main` est à jour jusqu'à la
> PR #2). Une nouvelle session doit d'abord faire `git fetch origin ccr-99c581ba-w0vhys` et repartir
> de cette branche.
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
| **`work/lab-fixes`** (lot de correctifs 5, 16, 18, 21, 22, 28, 29, 31) | ⏸ **tout est fait, en attente de la signature CP-2 (merge) par l'Owner** | branche, `7fdc8da`…`d10f294` |
| fde-kit itération 3 | à faire après le merge de lab-fixes | §11 |

**Prochaine action (Owner) :** trancher CP-2 de `lab-fixes` (voir §10.4 : une revue a trouvé un vrai
écart mineur, le renommage absent du trailer `Artifacts:`). Puis : PR `ccr-99c581ba-w0vhys` → `main`,
merge **uniquement sur demande explicite de l'Owner**.

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
| `work/lab-fixes/tasks.md` | 0.1.0 | approved ; T1–T6 + CP-1 faits, CP-2 en attente |
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

1. plan-lint : la vérif d'existence d'un ID de spec matche aussi les IDs supprimés cités dans le changelog.
2. `work/sdlc-rework/tasks.md` : 17 erreurs plan-lint ; plan-lint seulement informatif en CI.
3. Couverture d'evals (`eval_covers`) cherchée dans toute la suite, pas par feature.
4. ✅ (`2b8f327`)
5. ✅ lab-fixes T3 — `--dry-run` n'écrit plus rien sous `.runs/` (BHV-2, EVAL-2).
6. `eval_models.py` compte une erreur d'API comme un échec.
7. Cas `BEH-eval-correct` : demande un fichier hors `files_touched`.
8. Golden `remise-paliers` échoue pour 5 modèles sur 6.
9. ✅ `guard_paths.sh` lit `notebook_path` (`5a70c84`).
10. Pré-vol : compare la version du kit, pas celle de `plugin.json` (à trancher : texte BHV-2a vs ADR-2).
11. `LAB_ROOT` relatif + `--project` sur le même dossier.
12. `scoped_commit` stage tout le dossier de la feature (rapports de revue embarqués dans les commits de tâche — encore vu sur T6 de lab-fixes, qui embarque `CP-1-review.md`).
13. ✅ (`ed61c07`)
14. ✅ (`f4f151c`)
15. Le reviewer ne peut lancer ni `just` ni `git` (approbation demandée) : les revues CP retombent sur la lecture de code ou `pytest`/`ruff` directs. → voie Owner / allowlist reviewer.
16. ✅ lab-fixes T3 — `Artifacts:` = chemins réellement stagés, triés (BHV-3, EVAL-3). Voir 35 (renommages).
17. ✅ (`2f3fe92`)
18. ✅ lab-fixes T6 — docs `just eval-models` en positionnel, verrouillé par EVAL-7.
19. Isolation des essais de modèles : `--plugin-dir`/`--settings` restent des chemins du kit dans l'argv ; confinement complet = bac à sable OS (candidat ADR).
20. Un rejet de checkpoint consomme vite le budget (max 2) quand c'est la **prescription** du rejet qui est fausse : prévoir un « amendement de note de rejet » ou un rejet qui ne compte pas.
21. ✅ lab-fixes T5 — tampons `<date>-<layer>` (+ `-2`…), plus d'écrasement (BHV-6, EVAL-6).
22. ✅ lab-fixes T4 — `gate: lint-check test evals check-brand check-lock` (BHV-4, EVAL-4).
23. `eval_gate.sh` : filtre d'extensions (`.py|.toml|.ts…`) — une instance non-Python n'est pas gardée en fin de session.
24. `lab init` pas atomique : seul le justfile est restauré en cas d'échec (conforme ADR-8, mais surprenant).
25. `46ab6dc` porte un tag `[BHV-7]` parasite (périmètre itération 4).
26. `brand_denylist.txt` vide : `check-brand` passe à vide (voulu ? à confirmer avant la première mission).
27. ✅ (`1dbfd26`) — règle : aucun contrôle de gate ne dépend d'un état hors git.
28. ✅ lab-fixes T1+T2 — SIGINT/SIGTERM : drapeau STOP, workers drainés, aucun commit, groupes de process tués, tâches en vol → `pending`, `run_interrupted`, rc 130 (BHV-1, EVAL-1).
29. ✅ lab-fixes T6 — même cause que 18 (prompt « corrige partout » = invitation à la fuite de périmètre : leçon de planification).
30. ✅ (`2cf51a8`)
31. ✅ lab-fixes T3 — le message de budget nomme sa source (`LAB_BUDGET_USD` ou `budget_usd, <origine>`) (BHV-5, EVAL-5).
32. ✅ (`a2a282c`, `369bdec`)
33. Ne jamais manipuler `git stash` pendant que le travail d'une tâche y est mis de côté.

**Nouveaux, relevés pendant le run lab-fixes (session 3) :**

34. Au premier run lab-fixes, des agents ont **écrit leurs OQ directement dans `spec.md`** (artefact validé). Converties en amendements Owner (spec 0.2.0, 0.3.0). La décision « OQ d'agent → `.runs/`, écrit par le moteur » (itération 3) doit l'empêcher mécaniquement.
35. **Renommage absent du trailer `Artifacts:`** (revue CP-2, panéliste 1) : `git diff --cached --name-only` a la détection de renommage active ; un `a → b` stagé ne liste que `b`. Correctif : `--no-renames` dans `scoped_commit` (`lab/engine/orchestrate.py` ~l. 605) + un cas renommage dans EVAL-3. Écart à INV-3 « ni plus ni moins ». **C'est la décision ouverte de CP-2 (§10.4).**
36. Amorçage des trailers : les commits qui livrent un correctif du moteur sont faits par l'ancien moteur (T1–T6 de lab-fixes ont des `Artifacts:` incomplets). Documenté, protégé par NG-4 — à garder en tête pour toute feature qui modifie le moteur qui l'exécute.
37. Redémarrer l'orchestrateur à un checkpoint **re-paie le panel de revue** même si seule la signature manque (voulu : « une approbation n'est jamais court-circuitée »). Coût ≈ 1–3 $ par redémarrage. Piste : réutiliser un rapport dont le HEAD n'a pas bougé.
38. **L'état de run est gitignoré** (`.runs/state.json`, `journal.jsonl`, `.approvals/`) : dans une session cloud, il meurt avec le conteneur → un changement de session force un rejeu ou une reconstruction à la main (déjà vu à l'itération 1, revu ici). Piste : dériver l'état « done » de l'historique git comme le lint de capacité (`1dbfd26`), ou un export/import explicite de l'état.
39. `LAB_APPROVAL_SECRET` vit dans le scratchpad de la session : perdu avec elle. Un nouveau secret fonctionne, mais les jetons signés avec l'ancien deviennent invalides (sans conséquence tant qu'aucun jeton n'est en attente).

## 9. Environnement (session cloud)

- `just` installé via `uv tool install rust-just` (à refaire dans une nouvelle session si absent) ;
  `claude` CLI authentifié (2.1.322 en session 2).
- **Pas de démon Docker** (le bac à sable `regulated` ne peut pas tourner ici).
- **Push de tag refusé (403)** : seule la branche de travail peut être poussée.
- Limite de quota « 5 heures » déjà atteinte une fois : un run peut échouer en bloc.
- Règle : un commit ne part que si le pre-commit passe (`bash .githooks/pre-commit && git commit …`).
- Pour travailler sur le kit avec ses propres garde-fous : `claude --plugin-dir lab/plugin`.

## 10. Feature `work/lab-fixes` (session 3) — en attente de CP-2

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

## 11. Ensuite

1. Merge de lab-fixes (et item 35 si non corrigé à CP-2).
2. **fde-kit itération 3** : workflow de bout en bout, retours arrière R1–R7 (avec reset ciblé des
   dépendants), OQ d'agent écrites par le moteur dans `.runs/` (item 34), test goldfish à deux
   lecteurs (Haiku + modèle de l'implementer), interruption live sous Docker. Candidats à absorber :
   items 12, 15, 20, 37, 38.
3. Itération 4 : retro + rôle `improver` (propose, n'applique jamais).
4. Itération multi-outils : Copilot, opencode, Codex CLI ; spike promptfoo (ADR-12).
5. Reste du lot : 1–3, 6–8, 10–12, 15, 19, 20, 23–26, 33, 37–39.
