# Progress — passation de session (2026-11-12, mise à jour session 2)

> Point d'entrée pour reprendre le travail dans une nouvelle session. Branche :
> `ccr-d4884d69-odjnuk`. Lire ensuite, dans l'ordre : `work/fde-kit/spec.md` →
> `design.md` → `tasks.md`, puis `git log --format='%h %s%n%b'` (le **pourquoi** de chaque
> décision est dans les messages de commit).

## 1. Objectif

Faire du lab un **kit FDE portable** : un SDLC agentique qu'un FDE apporte sur chaque nouvelle
mission, adaptable au niveau d'organisation, avec des retours arrière automatiques quand un
agent n'atteint pas son objectif, et une amélioration continue gouvernée. Feature :
`work/fde-kit/`.

## 2. Où en sont les artefacts

| Artefact | Version | Statut |
|---|---|---|
| `work/fde-kit/spec.md` | 0.6.0 | validated |
| `work/fde-kit/design.md` | 0.4.0 | validated (ADR-1..11 accepted, ADR-12 proposed) |
| `work/fde-kit/tasks.md` | — | approved (itération 1 : 14 tâches, 5 checkpoints bloquants) |
| `lab/models/registry.toml` | — | rôles passés à la famille Claude 5 (voir §4) |

**Itérations prévues** (spec) : 1 kit portable (**en cours**) · 2 profils solo/squad/regulated ·
3 workflow de bout en bout, retours arrière R1–R7, test goldfish à deux lecteurs · 4 retro +
rôle `improver` (auto-amélioration gouvernée) · multi-outils (Copilot, opencode, Codex CLI ;
spike promptfoo, ADR-12).

## 3. Décisions de l'Owner (toutes prises par QCM, détail dans les commits)

- **Distribution** : 100 % plugin Claude Code côté FDE (`lab/plugin/`) ; rien d'outillage agent
  dans le repo client (INV-8) ; « mode instance » plus tard (NG-6).
- **Ce repo = le kit** ; démos `devis` et `booking` → `examples/` en instances autonomes.
- **Profils** `solo` / `squad` / `regulated` ; `--profile` obligatoire ; exemples en `squad`.
- **Retours arrière** : plan delta toujours humain ; OQ d'agent → `.runs/` (écrit par le moteur) ;
  reset ciblé des dépendants ; retros locales au FDE ; KPI mesuré d'abord.
- **Goldfish** (emprunté au pattern Elephant/Goldfish, pas le plugin) : test mesurable, deux
  lecteurs (Haiku + modèle de l'implementer), mesure seule, gardé seulement s'il réduit R3/R4.
- **Multi-outils** : Copilot, opencode, Codex CLI ; interactif d'abord ; nouvelle itération ;
  outil qui ne lit ses règles que dans le repo → attend le mode instance.
- **promptfoo** : spike dans l'itération multi-outils (ADR-12), adoption sur preuve.
- **Improver** : itération 4 (BHV-12, INV-16) — propose, jamais n'applique.
- **Run itération 1 dans la session cloud**, checkpoints signés sur instruction de l'Owner.

## 4. Modèles (campagne du 2026-11-12, 17,14 $)

`[roles]` : implementer `claude-sonnet-5-5`, planner + reviewer `claude-opus-5-5`,
eval-runner `claude-haiku-5-5`. Preuve = non-régression (pas supériorité : n=1 par golden).
Scorecards : `lab/models/scorecards/2026-11-12-*.md|jsonl`.

## 5. État du run (itération 1) — session 2 (redémarrage complet demandé par l'Owner)

Le `state.json` n'avait pas survécu au changement de session : l'Owner a choisi un **rejeu
complet** pour observer tout le workflow. T1–T10 ont été rejoués (commits « journal seul »,
travail déjà présent : `15f628c`…`0b09785`), puis la suite a avancé.

| Nœud | État | Commit(s) |
|---|---|---|
| T1–T10, CP-1, CP-2 | ✅ (rejeu) | réel : `efcc57d`…`a44e003` ; rejeu : `15f628c`…`0b09785` |
| T7 | ✅ débloqué par le delta de plan `e86d8c4` (vérif laissée à l'orchestrateur) | `d7b434a` |
| T9 | ✅ après **rejet CP-3** (test hors scope → delta `314bf39`) | `e8da4a2` + `cda972e` |
| CP-3 | ✅ (gate-ci + audit du move + dry-runs faits côté Owner) | `1f183f0` |
| T15 | ✅ **voie Owner** (fichiers protégés `.claude/` → `lab/plugin/`) | `f93438a` (+ `2be6b62`) |
| T11 | ✅ (scindé : partie agent, après blocage chemins protégés) | `50f9c61` |
| T12, T13 | ✅ ; T13 retravaillé après **2 rejets CP-4** (accès des essais aux clés de réponse) | `a243a5d`, `ac9aed9` |
| CP-4 | ✅ campagne ADR-11 (3 modèles de prod, 3,77 $) : chaîne 9/9, behavioral 8/11 chacun | `0b32947` |
| T14 | ✅ après **rejet CP-5** (ruff format) — 1ᵉʳ rework avec le `Why:` qui cite le rejet | `10293ef` + `e72d97e` |
| CP-5 | ✅ signé sur décision de l'Owner (panel 3 lentilles WARN ×3, aucun bloquant) → PR vers `main` | `b5579d9` |

Contrôles live CP-4 faits : **EX-5 ✅** (un `claude -p` avec l'argv du run ne peut pas écrire
`.approvals/CP-1` — refusé par le hook `guard_paths` du plugin) ; **BHV-2b ✅** (une session
`--plugin-dir lab/plugin` reçoit les 8 règles via SessionStart) ; **`--settings` sous `--bare` :
non concluant** (`--bare` n'accepte pas l'auth OAuth de la session ; le moteur ne passe jamais
`--bare`).

## 6. Améliorations du workflow faites pendant ce run (hors plan, Owner)

Chaque blocage du run a été transformé en garde-fou du moteur (le pourquoi est dans chaque commit) :

| Commit | Amélioration | Déclencheur |
|---|---|---|
| `f4f151c` | **Scope leak** : une tâche verte grâce à des fichiers hors `files_touched` est renvoyée à l'agent (sinon le commit est rouge alors que le journal dit vert) | CP-3 BLOCK (T9) |
| `ed61c07` | **Voie Owner** (`**agent:** owner`) + **lint de capacité** (tâche agent sur chemin protégé = erreur ; prompt demandant `git mv`/`git rm`/`just` = warning) | T11 bloqué (3ᵉ cas après T6, T7) |
| `94f273e` | Trajectory guard : `owner_signed` journalisé = preuve d'une tâche Owner | revue CP-4 |
| `2f3fe92` | Le `Why:` d'un commit auto de rework cite le rejet de checkpoint | revue CP-4 |
| `4bf2b48` | Essais de modèles : fichier de rôle copié dans le cwd de l'essai, plus de chemin du kit ni d'`--add-dir` (équité EVOLUTION.md) | revue CP-4 (3 passes) |
| `876a54d` | `just lint-check` du projet fait partie du gate de tâche | CP-5 BLOCK (T14) |
| `5a70c84` | `guard_paths.sh` lit aussi `notebook_path` (NotebookEdit) | revue CP-5, lab-fix 9 |
| `deffc82` | Un rejet en attente est honoré avant de payer un panel de revue | redémarrage à CP-5 |
| `3c5b3a5` | Trajectory guard : seulement les commits `Run: auto` ; jeton signé archivé = preuve Owner | revue CP-5 |

Leçons de planification : une tâche scindée doit rester verte à chaque étape (T15 a dû absorber
deux lignes de test) ; un rejet doit prescrire le **besoin** (« le modèle lit son fichier de
rôle sans voir les clés »), pas un mécanisme (l'`--add-dir` prescrit a ouvert une fuite).

## 7. Prochaine action

Itération 1 **terminée** (20 nœuds ✅, coût agents du run 4 : 8,37 $). L'Owner a décidé :
PR `ccr-99c581ba-w0vhys` → `main` (correctifs moteur dans la même PR), **merge par l'Owner** sur
GitHub, puis tag **`v0.1.0`** sur `main` après le merge. À annoncer : O-6 (une session dans le kit
sans `--plugin-dir lab/plugin` n'a plus de garde-fous). Ensuite : itération 2 (profils
solo/squad/regulated) et une feature dédiée au lot de correctifs ci-dessous ; recalibrer
`reviewer.md` via la boucle EVOLUTION (WARN sur code propre sous conditions réelles).

## 8. Lot de correctifs du lab (hors plan)

Faits : 4 (`2b8f327`), 9 (`5a70c84`), 13 (`ed61c07`), 14 (`f4f151c`), 17 (`2f3fe92`) — marqués ✅.

1. plan-lint : la vérif d'existence d'un ID de spec matche aussi les IDs supprimés cités dans le changelog.
2. `work/sdlc-rework/tasks.md` : 17 erreurs plan-lint ; plan-lint seulement informatif en CI.
3. Couverture d'evals (`eval_covers`) cherchée dans toute la suite, pas par feature.
5. `--dry-run` écrit un faux `run_end` dans le journal (encore observé : il fausse `just report`).
6. `eval_models.py` compte une erreur d'API comme un échec.
7. Cas `BEH-eval-correct` : demande un fichier hors `files_touched`.
8. Golden `remise-paliers` échoue pour 5 modèles sur 6.
9. ✅ `guard_paths.sh` ignore `notebook_path` (`5a70c84`).
10. Pré-vol : compare la version du kit, pas celle de `plugin.json` (à trancher : texte BHV-2a vs ADR-2).
11. `LAB_ROOT` relatif + `--project` sur le même dossier.
12. `scoped_commit` stage tout le dossier de la feature (rapports de revue embarqués dans les commits de tâche).
14. ✅ Vérif sur l'arbre de travail ≠ contenu du commit (`f4f151c`).
15. Le reviewer ne peut lancer ni `just` ni `git` (approbation demandée) : les revues CP retombent sur la lecture de code. Même famille que 13 → voie Owner / allowlist reviewer.
16. Rejeu complet : commits « journal seul » avec des `Artifacts:` faux (le trailer recopie `files_touched`, pas les fichiers réellement modifiés).
17. ✅ `Why:` des commits auto de rework (`2f3fe92`).
18. Syntaxe `just eval-models layer=… live=1` des docs/plans fausse (paramètres positionnels).
19. Isolation des essais de modèles : `--plugin-dir`/`--settings` restent des chemins du kit dans l'argv et l'environnement des hooks ; confinement complet = bac à sable OS (candidat ADR).
20. Un rejet de checkpoint consomme vite le budget (max 2) quand c'est la **prescription** du rejet qui est fausse : prévoir un « amendement de note de rejet » ou un rejet qui ne compte pas.
21. `just eval-models` écrit `latest.*` sans tampon : la 2ᵉ couche écrase la 1ʳᵉ (behavioral reconstruit depuis le log).
22. `just gate` lance `lint` **mutant** : vérifier reformate le travail d'un autre (à remplacer par `lint-check` dans `gate`).
23. `eval_gate.sh` : filtre d'extensions (`.py|.toml|.ts…`) — une instance non-Python n'est pas gardée en fin de session (itération 2).
24. `lab init` pas atomique : seul le justfile est restauré en cas d'échec (conforme ADR-8, mais surprenant).
25. `46ab6dc` porte un tag `[BHV-7]` parasite (périmètre itération 4).
26. `brand_denylist.txt` vide : `check-brand` passe à vide (voulu ? à confirmer avant la première mission).
27. ✅ Vert en local, rouge en CI (PR #1) : le lint de capacité lisait les tâches « done » dans `.runs/state.json`, **gitignoré** — corrigé en les dérivant de l'historique git (`1dbfd26`). Règle à retenir : aucun contrôle de gate ne doit dépendre d'un état hors git.

## 9. Environnement (session cloud)

- `just` installé via `uv tool install rust-just` ; `claude` CLI 2.1.322 authentifié.
- Limite de quota « 5 heures » déjà atteinte une fois : un run peut échouer en bloc.
- Règle retenue : un commit ne part que si le pre-commit passe (`bash .githooks/pre-commit && git commit …`).
