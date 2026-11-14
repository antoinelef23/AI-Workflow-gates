# Progress — passation courte (mise à jour 2026-11-14)

> Point d'entrée d'une nouvelle session. L'historique complet des sessions 1 à 5 (décisions,
> backlog détaillé des lab-fixes §8, runs, PR #1 à #14) est dans
> `docs/history/progress-2026-11-14.md` ; le **pourquoi** de chaque décision est dans les messages
> de commit (`git log --format='%h %s%n%b'`).

## Où on en est

| Chantier | État |
|---|---|
| fde-kit itérations 1 et 2 (kit portable, profils) | ✅ mergées (PR #1, #2) |
| Lot lab-fixes + correctifs PR #4 à #12 | ✅ mergés le 2026-11-14 |
| fde-kit itération 3 — conception | ✅ spec 0.9.0 + design 0.8.0 validés (PR #13), plan `tasks.md` 0.3.0 approuvé (PR #14) |
| fde-kit itération 3 — **tranche 1** (T23–T26 : `spec-lint`, `design-lint`, état de run v2 avec compteurs persistés, `lab next`) | ✅ CP-8 validé par décision Owner ; mergée (PR #15) |
| fde-kit itération 3 — reste (T27–T35 : routes R1..R7, OQ par le moteur, goldfish, version 0.3.0) | ⏸ run arrêté par l'Owner (trop d'arrêts) ; **à re-planner** après le cas réel |
| Dépôt `portable` (Claudo-portable) | branches `drop-windows`, `models-latest-only` poussées, sans PR |

## Mandat autonome (décidé par l'Owner par QCM le 2026-11-14)

Sous un objectif « finir le produit », le travail avance **sans interaction avec l'Owner** :

- **Périmètre** : toute la spec fde-kit — reste de l'itération 3 (T27–T35), itération 4 (retro,
  improver), itération multi-outils (Copilot, opencode, Codex CLI).
- **Checkpoints** signés par Claude : approuvé si `just gate-ci` est vert dans un **clone propre** ET
  si le panel de revue n'est pas BLOCK ; sinon rejet avec ses constats (2 au plus), puis correction
  en voie Owner. Chaque décision est consignée dans `tasks.md`.
- **Budget** : pas de plafond pour le travail d'agent facturé, pas de confirmation avant un run complet.
- **Cas réel** : Claude le mène seul, sur une instance neuve (`lab init`).
- **Multi-outils** : conformité testée par shims seulement ; chaque outil reste « live non vérifié »
  jusqu'à la connexion de l'Owner (INV-14 refuse alors un run orchestré avec cet outil).
- **Conception des itérations 4 et multi-outils** : option recommandée par design-scout, consignée
  « décidé sous délégation de l'Owner » dans le changelog du design et ici.
- **Versions** : 0.3.0, 0.4.0, 0.5.0, une par itération ; tags poussés (plus `v0.1.0` / `v0.2.0`), ou
  commandes listées ici si le push est refusé.
- **Rôle goldfish** : Haiku 5.5 l'obtient si, sur chaque spec de la campagne, l'isolement est prouvé
  pour les deux lecteurs et si Haiku rend une prédiction lisible pour chaque EX testable ; les
  scores sont rapportés, non jugés.
- **Merges** : autorisés quand la CI est verte.

## Prochaines étapes (décidées par l'Owner le 2026-11-14)

1. **Cas réel** (mené par Claude, mandat ci-dessus) : `lab init` d'une instance neuve (profil
   `squad`), une petite feature, spec → design → plan → run, checkpoint signé selon les critères
   du mandat. But : éprouver les gates comme un FDE et mesurer ce qui ralentit.
2. **Re-planner T27–T35** avec moins d'arrêts : T28 (OQ écrite par le moteur, plus jamais dans
   `spec.md`) en premier ; CP-9 et CP-10 fusionnés ; les tâches voie Owner regroupées ; un seul
   redémarrage du moteur au plus.
3. Re-mesure facturée des deux cas modifiés par la PR #8.
4. Itération 4 (retro, improver) puis itération multi-outils : design-scout, décisions sous
   délégation, plan, run ; version et tag par itération.

## Constats du run du 2026-11-14 (à reprendre au re-planning)

- Moteur : T23–T26 réussis à la 1ʳᵉ tentative, 2 à 4 min et ≈ 0,40 $ chacun (2,57 $ au total).
- Arrêts : décisions de conception (normal) ; 4 checkpoints bloquants, 2 redémarrages
  obligatoires, 2 tâches voie Owner, 2 campagnes facturées dans le plan ; T25 bloqué par un
  `files_touched` trop étroit (défaut du plan, réglé par un delta) ; l'agent a encore écrit son OQ
  dans `spec.md` (ancien prompt, corrigé par T28 à venir) — édition annulée.
- `state.json` absent au démarrage : recréé à la main depuis git (sinon rejeu facturé de T1–T22).
  T24/T25 règlent ce cas : les tâches livrées se lisent dans git.
- Lints sur les 6 features : constats réels (OQ-12 ouverte dans fde-kit, ADR sans `Anchored on:`
  dans les designs anciens) et cas de rigueur à revoir (BHV-1a retiré mais signalé non couvert ;
  OQ tranchées sans le mot « résolue »).
- Trou du moteur vu en CI (PR #15) : la fixture `tests/fde_kit/fixtures/next/build/` de T26 était
  ignorée par `.gitignore` (`build/`) ; le commit scopé l'a sautée sans rien dire et le gate local
  passait grâce aux fichiers sur disque. À couvrir au re-planning : `scoped_commit` doit refuser un
  chemin de `files_touched` ignoré par git.

## Décisions Owner en attente

- Items du backlog lab-fixes 2, 6, 10, 15, 19, 20, 23–26, 33, 37, 41, 42 (détail, preuves et
  options : `docs/history/progress-2026-11-14.md` §8). Item 38 (état de run perdu) : traité en
  partie par T24/T25.
- Tags `v0.1.0` (`b64b227`) et `v0.2.0` (`54fecfc`) ; run `regulated` réel sous Docker (ADR-15).

## Environnement et règles

- **WSL Ubuntu uniquement** : clone `~/work/lab-fixes` ; `just`, `uv`, `claude` installés ;
  `UV_HTTP_TIMEOUT=300`. Push depuis Windows : `git fetch //wsl.localhost/Ubuntu/home/antoine/work/lab-fixes <b>:refs/heads/<b>` puis `git push`.
- Vérification unique : `just gate-ci` (rc 0 attendu). Commit seulement si
  `bash .githooks/pre-commit` passe.
- Lancer un run : `export LAB_APPROVAL_SECRET="$(cat ~/.lab-secrets/approval)"` puis
  `python3 -u lab/engine/orchestrate.py work/<feature>` ; arrêt propre : SIGINT. Ne jamais
  committer le secret.
- Checkpoints : signés seulement sur instruction de l'Owner (`approve.sh` / `reject.sh`) ; merge
  seulement sur demande explicite. Tout ce qui est facturé : smoke d'abord, accord avant le run
  complet.
