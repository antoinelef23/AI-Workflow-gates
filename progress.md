# Progress — passation de session (2026-11-12)

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

## 5. État du run (itération 1)

| Nœud | État | Commit |
|---|---|---|
| T1–T4 | ✅ done (1ᵉʳ essai) | `efcc57d` `318d5c6` `81cbfee` `2a04e35` |
| CP-1 | ✅ approuvé (WARN sans bloquant ; contrôle live plugin OK) | `7b32145` |
| T5 | ✅ done | `89d2532` |
| CP-2 | ✅ approuvé (aucune PR ouverte vérifiée) | `b62cdde` |
| T6 | ✅ done — **déplacement fait à la main** (exception autorisée « une seule fois », agent sans droit `git mv`) | `90fb9f9` (+ `c2aebe2` auto) |
| **T7** | 🛑 **blocked** dans `state.json` — travail fait, vérif verte (1063 evals lancées par Claude), mais l'agent refusait de conclure sans lancer `just` lui-même | commité à la main sur instruction de l'Owner (changement de compte) — voir `git log -1 -- examples/devis/pyproject.toml` |
| T8, T10 | ✅ done | `6f3948d` `a44e003` |
| T9, CP-3, T11–T14, CP-4, CP-5 | ⏭ skipped (dépendent de T7) | — |

Coût agents du run : **9,88 $** (journal) ; total session ≈ 29 $ avec campagne et contrôles.
`state.json` et `journal.jsonl` sont dans `work/fde-kit/.runs/` (gitignorés).

## 6. Prochaine action (décidée, PAS encore faite)

**Delta de plan approuvé par l'Owner** (« Amender le plan ») pour T7 **et** T9 : ajouter à leur
prompt « la vérification (`verify`) est exécutée par l'orchestrateur après toi ; vérifie
localement avec l'équivalent `uv run pytest -m eval` (dans `examples/<x>`) — n'essaie pas de
lancer `just` ». Puis :

1. Modifier les prompts de T7 et T9 dans `work/fde-kit/tasks.md` + noter le delta dans
   `approved_by` ; `bash .githooks/pre-commit && git commit` (format canonique, Why: plan gap).
2. Les fichiers de T7 (`examples/devis/{pyproject.toml,uv.lock,justfile,.lab/,work/README.md,work/_templates/}`)
   sont **commités** (exception manuelle demandée par l'Owner avant changement de compte). À la
   reprise, T7 est rejoué : l'agent trouve le travail fait, l'orchestrateur lance la vérif et
   confirme ; le commit auto de T7 sera vide ou ne contiendra que le journal du run.
3. Relancer le run (reprend à T7) :
   ```bash
   export LAB_APPROVAL_SECRET="$(openssl rand -hex 32)"   # nouveau secret : l'ancien vivait dans le scratchpad
   python3 lab/engine/orchestrate.py work/fde-kit          # ou en détaché + guetteur sur le log
   ```
4. **CP-3** (bloquant) : relire le commit de déplacement pur `90fb9f9` (content_guard aveugle aux
   fichiers déplacés), `lab run --project examples/<x> --dry-run` sur les deux exemples, puis
   **redémarrage obligatoire** de l'orchestrateur avant T11 (bascule `.claude/` → `lab/plugin/`).
5. **CP-4** : campagne live behavioral + chain lancée par l'Owner (facturée, ADR-11).
6. **CP-5** : merge, humain.

Signature d'un checkpoint : `LAB_APPROVAL_SECRET=… bash lab/engine/approve.sh CP-n work/fde-kit`.

## 7. Lot de correctifs du lab (hors plan — à traiter dans une feature séparée)

1. plan-lint : la vérif d'existence d'un ID de spec matche aussi les IDs supprimés cités dans le changelog.
2. `work/sdlc-rework/tasks.md` : 17 erreurs plan-lint (chevauchement `justfile`, `tests/sdlc_rework/`) ; plan-lint seulement informatif en CI.
3. Couverture d'evals (`eval_covers`) cherchée dans toute la suite, pas par feature.
4. `orchestrator.lock` non ignoré — **corrigé** (`2b8f327`).
5. `--dry-run` écrit un faux `run_end` dans le journal.
6. `eval_models.py` compte une erreur d'API comme un échec (dont 3 fausses violations de chaîne).
7. Cas `BEH-eval-correct` : demande un fichier hors `files_touched`.
8. Golden `remise-paliers` échoue pour 5 modèles sur 6 (oracle ou tâche à revoir).
9. `guard_paths.sh` ignore `notebook_path` (CP-1, écart 2).
10. Pré-vol : compare la version du kit, pas celle de `plugin.json` (CP-1, écart 3).
11. `LAB_ROOT` relatif + `--project` sur le même dossier (CP-1, écart 4).
12. `scoped_commit` stage tout le dossier de la feature (rapports de relecture régénérés embarqués dans les commits de tâche) (CP-2, écart 1).
13. Le planner ne vérifie pas que chaque tâche tient dans les outils autorisés des agents (T6 `git mv`, T7/T9 `just`) — premier cas concret pour l'`improver`.

## 8. Environnement (session cloud)

- `just` installé via `uv tool install rust-just` ; `claude` CLI 2.1.322 authentifié.
- Limite de quota « 5 heures » déjà atteinte une fois : un run peut échouer en bloc.
- Règle retenue : un commit ne part que si le pre-commit passe (`bash .githooks/pre-commit && git commit …`).
