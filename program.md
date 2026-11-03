# CARLA Agent execution contract

Use domain skills and actual `carla-agent --help` / `schema`. Controller and
research runner own state; the coding agent owns intent and explanations.

1. Read the profile and run connection doctor; discover actual capabilities.
2. Read-only requests do not authorize actors or changed world settings.
3. Mutations require a dedicated exclusive instance, matching client/server and
   pinned expected version. Never switch maps implicitly.
4. Use sessions for owned actors and bounded ticks; close when done. Do not kill
   by port, remove unrelated actors, or restore after episode/ownership conflicts.
5. Use capture run for its supported RGB/RayCast recipes. Other sensor workflows
   follow their source-backed native guidance with their own bounded lifecycle;
   never take over a CLI/research lease or bypass a rejected operation. Raw files
   and frame metadata establish observed results.
6. Research requires a frozen finite plan and verified local server process.
   Execution, validity and improvement verdict remain separate.
7. Preserve failed trials. Old metrics are never a new result.
8. First version supports parameter tradeoffs, not autonomous source editing.
   A selected candidate is not a code merge or product release.
9. Discover granular skills offline with `skills list/show`. Their execution
   metadata distinguishes wrapped commands, native workflows and dependencies;
   skill presence is not a claim of current runtime support.

Previous local instructions remain in a private migration backup; they are not part of the distributed plugin.
