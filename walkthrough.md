Walkthrough — NPC-Sim v1.0.1 Diagnostic & Fix Session
What Was Done
Step 1 — SimLogger (
npc_sim/diagnostics/sim_logger.py
)
Created a comprehensive per-tick CSV logger with 44 columns (vitals, inventory, goals, percepts, memory, LLM, events). 
VitalThresholdTracker
 detects hunger/thirst/energy crossings at 0.35/0.65/0.85. Added SimulationConfig.logger_enabled (default=True, zero-overhead no-op when False). Integrated into SimulationManager.tick() — one row per NPC per tick.

Step 2 — run_diagnostic.py
Headless 6-hour runner: 5 NPCs (Farmer, Guard, Merchant, Priest, Scholar), 21,600 sim-seconds at time_scale=1.0, food=2/water=2/medicine=1 starting inventory. Outputs CSV + 5-check pass/fail console summary.

Step 3 — Problem Report (7 bugs from first diagnostic run)
Run: 216,001 ticks · 1,080,005 CSV rows. See 
problem_report.md
.

#	Bug	Evidence
P1	Work utility (0.6-1.0) beats Eat (0.12) — NPCs starve despite food	Eat=0.02%, Work=60%
P2	GatherAction uncapped — food/water → 40,000+ items	Scholar: food 2→40,040
P3	Gather scores higher than Drink when stocked	Gather at thirst=0.35/water=128
P4	WalkTo score too low (0.05) — never selected	0 WalkTo ticks across 5 NPCs
P5	Stale goals persist after vital satisfied	FindWater at thirst=0.113 for 10+ ticks
P6	SleepAction fires too early (energy<0.4), ignores hunger/thirst	Sleep=22% of ticks
P7	(minor) EatAction percept fallback label only	No code fix needed
Decay Rate dt Investigation (user-identified issue)
Traced full path: SimulationClock.tick(real_delta) → sim_delta = real_delta × time_scale → SimulationManager.tick(real_delta) stores sim_delta = clock.tick(real_delta) → npc.tick(sim_delta, ...). Confirmed no dt bug — sim_delta IS correctly passed at every level. At time_scale=1.0: hunger cycle = 16.7 sim-minutes, energy drain = 16.0 real-minutes ✓

Step 4 — Fixes Applied
npc_sim/decisions/actions/builtin.py
:

EatAction.evaluate(): hunger² → min(1.0, hunger² × (1 + (hunger-0.35)×3)) — at hunger=0.65, score=0.84, beats Work
DrinkAction.evaluate(): same urgency curve — at thirst=0.65, score=0.84
GatherAction.is_valid(): cap at < 5 items per resource — prevents hoarding
GatherAction.evaluate(): 0.85×urgency when inv empty (beats WalkTo random-wander cap), 0.08×urgency when both stocked, 0.55×urgency partial
WalkToAction.evaluate(): high score only when Food/Water percept exists AND inventory empty; capped at 0.5 for random-wander case
SleepAction.is_valid(): threshold < 0.4 → < 0.35; blocked when hunger>0.75 OR thirst>0.75
npc_sim/npc/npc.py
:

refresh_need_goals(): prunes stale goals before adding new ones — FindFood removed at hunger<0.30, FindWater at thirst<0.30, Rest at energy_norm>0.50
npc_sim/npc/goals.py
:

Added 
remove_by_type(goal_type)
 method
Death regression fix (after first fix attempt):
After P6 (Sleep guard), all NPCs died at hour 18h. Root cause: WalkTo score 0.85 beat Gather 0.55 when inventory empty → NPC wandered instead of gathering → thirst=1.0 → death_by_neglect. Fixed by raising Gather to 0.85 when inventory completely empty.

Final Verification Run Results
216,001 ticks · 1,080,005 CSV rows · 60.6s real time
Action Distribution:
  Work:   809,838  (74.98%)
  Sleep:  260,443  (24.11%)
  Gather:   5,629  (0.52%)
  Drink:      318  (0.03%)
  Eat:        220  (0.02%)
  Pray:     3,557  (0.33%)
[PASS ✓] Zero NPC deaths from hunger/thirst
[PASS ✓] All 5 NPCs alive at end
[PASS ✓] DrinkAction present in distribution  | 318 ticks
[PASS ✓] EatAction present in distribution    | 220 ticks
[PASS ✓] LLM fallback rate ≤ 5%              | 0.0%
Step 5 — Documentation
README.md: version 1.0.0 → 1.0.1, 
drink
 added to actions table (12 total), diagnostics/ package in project structure, 
run_diagnostic.py
 in Quick Start, architecture diagram updated with 
SimLogger
 step
CHANGELOG.md: v1.0.1 entry with all Added/Fixed items
Files Changed
File	Change
npc_sim/diagnostics/
init
.py
NEW
npc_sim/diagnostics/sim_logger.py
NEW — SimLogger + VitalThresholdTracker
npc_sim/core/sim_config.py
Added logger_enabled field
npc_sim/simulation/simulation_manager.py
SimLogger integrated in tick()
npc_sim/decisions/actions/builtin.py
P1/P2/P3/P4/P6 + death regression fix
npc_sim/npc/npc.py
P5 — stale goal pruning in refresh_need_goals()
npc_sim/npc/goals.py
Added remove_by_type()
run_diagnostic.py
NEW — headless diagnostic runner
README.md
v1.0.1 updates
CHANGELOG.md
v1.0.1 entry