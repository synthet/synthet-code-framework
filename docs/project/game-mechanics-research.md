# Game Mechanics Research: Terraria, Starbound, and Oxygen Not Included

Date: 2026-07-08

## Purpose

This document identifies reusable design patterns from **Terraria**, **Starbound**, and **Oxygen Not Included** that may be adapted for our game. It focuses on mechanics and system ideas, not protected expression. Do **not** copy names, art, story, UI layouts, exact numbers, item lists, enemy designs, or proprietary formulas from the reference games.

## Executive recommendations

1. **Use layered progression gates rather than one linear campaign.** Combine Terraria-style boss/world-state milestones, Starbound-style planetary/environmental tiers, and Oxygen Not Included-style technology thresholds so players always have several viable next goals.
2. **Make the world simulation produce goals.** Pressure, heat, oxygen, contamination, resource depletion, biome danger, NPC needs, and settlement logistics should naturally create problems instead of relying only on authored quests.
3. **Reward building as a strategic system.** Housing, rooms, machines, wiring, transport, farms, and defensive layouts should grant functional benefits, not merely decoration.
4. **Support both exploration and engineering play.** Terraria and Starbound reward outward exploration; Oxygen Not Included rewards closed-loop base design. Our strongest opportunity is a loop where exploration acquires materials/anomalies and engineering converts them into long-term survival capacity.
5. **Keep inspiration at the abstraction level.** The safest reusable mechanics are broad systems: crafting chains, biome hazards, procedural worlds, automation signals, colony needs, NPC recruitment, environmental simulation, and milestone-driven unlocks.

## Reference-game mechanics worth adapting

### Terraria-inspired mechanics

Terraria is strongest at turning a 2D sandbox into a sequence of escalating discoveries. Useful mechanics to adapt:

- **Milestone bosses that alter the world state.** Boss defeats can unlock new materials, enemy sets, hazards, regions, or NPC services. This creates memorable progression moments without forcing a fully linear campaign.
- **Biome-driven resources and risks.** Distinct areas can have exclusive materials, enemies, weather, ambient hazards, and building incentives.
- **Crafting as discovery.** New ingredients can reveal recipes and encourage players to revisit old systems with new tools.
- **NPC settlement utility.** Player-built housing can attract specialists who provide shops, services, quests, fast travel, crafting upgrades, or information.
- **Events and invasions.** Time-, location-, or trigger-based events can temporarily alter the normal rules and create preparedness checks.
- **Tool and mobility progression.** Pick speed, mining reach, hooks, wings, mounts, grapples, dash abilities, and terrain traversal tools can expand accessible space.
- **World difficulty transitions.** A major milestone can remix an existing world with new threats and rewards, making established bases and routes matter again.

Design caveats:

- Avoid boss gating becoming opaque. Give in-game hints, NPC guidance, environmental clues, and objective breadcrumbs.
- Avoid pure stat inflation. Each tier should add new verbs, constraints, or environmental interactions.

### Starbound-inspired mechanics

Starbound is useful as a model for broad exploration, modular progression, and colony/crew fantasy. Useful mechanics to adapt:

- **Procedural destinations with explicit threat tiers.** Worlds, derelicts, biomes, or regions can communicate danger through a rating tied to enemies, loot, hazards, and required gear.
- **Environmental protection gear.** Radiation, cold, heat, vacuum, pressure, toxins, spores, and corrosive atmospheres can gate exploration through equipment and preparation.
- **Ship/mobile-base progression.** A headquarters that travels with the player can become a persistent upgrade sink, storage hub, crew home, and mission launcher.
- **Crew recruitment from side activities.** Helping settlements or completing generated tasks can produce recruitable specialists with passive bonuses or active support.
- **Generated quests for infinite texture.** Small procedural requests can add local context: retrieve, escort, repair, defend, scan, deliver, map, or stabilize.
- **Colonies/tenants as economic systems.** Rooms with different tags or amenities can attract different resident types, producing rent, services, rumors, or defense.
- **Optional story path.** Main missions can exist without blocking most sandbox content, reducing friction for players who prefer self-directed play.
- **Tech/mobility trials.** New abilities can be introduced through short challenge spaces that teach their use before the player relies on them in the open world.

Design caveats:

- Procedural planets can feel interchangeable if they only reshuffle visuals. Tie procedural generation to systemic differences: atmosphere, resources, enemy ecology, settlement economy, physics modifiers, and machine constraints.
- Generated quests need strong templates and local consequences; otherwise they become busywork.

### Oxygen Not Included-inspired mechanics

Oxygen Not Included is strongest at systemic colony survival, material simulation, and automation. Useful mechanics to adapt:

- **Gas, liquid, and heat simulation.** Air quality, fluid flow, temperature, pressure, and phase changes can create emergent engineering challenges.
- **Closed-loop resource systems.** Waste can become input; power, water, oxygen, food, heat, and byproducts can form chains that reward planning.
- **Duplicant-style worker priorities.** If our game has NPC workers, assignable jobs, skills, schedules, morale, and pathing constraints can turn base layout into gameplay.
- **Stress/morale as operational pressure.** Comfort, decor, food quality, crowding, danger, and downtime can affect worker reliability.
- **Automation and sensors.** Switches, logic gates, pressure plates, thermometers, gas sensors, fluid sensors, timers, and thresholds can let players build self-regulating systems.
- **Material properties matter.** Thermal conductivity, melting point, contamination, density, hardness, and permeability can differentiate resources beyond rarity.
- **Research that unlocks systems, not just stats.** Research can open new production chains, automation controls, habitat modules, and hazard-management tools.
- **Failure cascades.** A small oxygen shortage, heat leak, polluted reservoir, or power brownout can escalate, creating memorable recovery stories.

Design caveats:

- Full-fidelity simulation can be expensive and hard to teach. Start with readable approximations and expose clear overlays.
- Failure cascades should be recoverable. Players need alarms, pause/planning tools, emergency modes, and low-tech fallback options.

## Mechanics matrix

| Mechanic pattern | Reference strength | How we may adapt it | Why it fits | Risk / mitigation |
| --- | --- | --- | --- | --- |
| Boss or milestone world-state changes | Terraria | Major enemies, expeditions, or projects unlock new global hazards/resources | Creates memorable phase changes | Provide strong in-game hints and reversible preparation windows |
| Biome-specific resource loops | Terraria, Starbound | Each biome has unique materials, hazards, ecology, and settlement benefits | Makes exploration purposeful | Avoid palette-swap biomes; give each biome at least one systemic rule |
| Environmental gear gates | Starbound | Suits/modules protect against heat, cold, pressure, vacuum, toxins, radiation | Turns preparation into progression | Avoid binary pass/fail; allow temporary consumables and risky shortcuts |
| Mobile base / ship hub | Starbound | Persistent hub for storage, crew, crafting, mission selection, upgrades | Connects exploration sessions | Prevent hub from replacing planetary/base building entirely |
| NPC housing and specialists | Terraria, Starbound | Build rooms to attract specialists, tenants, or crew with services | Makes construction functional | Use original archetypes and avoid copying named NPC roles |
| Generated local tasks | Starbound | Procedural requests tied to settlements, anomalies, or base incidents | Adds repeatable goals | Require local consequence and varied rewards |
| Gas/liquid/thermal simulation | Oxygen Not Included | Simplified atmosphere, fluid, pressure, and heat layers | Creates emergent engineering | Use overlays, limits, and coarse simulation for performance/readability |
| Automation networks | Oxygen Not Included | Sensors and signal wires control machines, doors, vents, pumps, turrets | Rewards mastery and creativity | Start with simple threshold sensors before complex logic |
| Worker schedules/priorities | Oxygen Not Included | NPCs have roles, skills, needs, and task priorities | Adds life to settlements | Keep UI manageable; offer presets |
| Failure cascades | Oxygen Not Included | Power, oxygen, heat, morale, or contamination failures can chain | Produces memorable stories | Add alarms, pause, emergency overrides, and recovery paths |
| Optional story over sandbox | Starbound | Story missions are valuable but not mandatory for most play | Respects player agency | Gate key tutorials outside optional story so sandbox players learn systems |
| Ability challenge rooms | Starbound | Short trials teach new traversal/build abilities | Smooths onboarding | Keep them brief and reusable as optional mastery tests |

## Proposed combined core loop

1. **Explore** a biome, planet, cavern, ruin, or asteroid layer.
2. **Extract** materials, samples, data, artifacts, recruits, or machine parts.
3. **Return and engineer** upgrades, rooms, automation, defenses, life support, or vehicles.
4. **Stabilize** colony/base systems against oxygen, heat, power, water, morale, attacks, or contamination problems.
5. **Unlock** a milestone: new biome access, new hazard protection, a boss/anomaly, a hub upgrade, or a world-state shift.
6. **Revisit** old locations with new tools and changed constraints.

This loop blends Terraria's escalation, Starbound's expedition fantasy, and Oxygen Not Included's engineering depth while remaining a distinct design.

## Prioritized mechanics for an MVP

### Tier 1: High value, manageable complexity

- Biome-specific materials and hazards.
- Crafting tiers with utility upgrades, not just damage/defense increases.
- Player-built rooms that attract NPC specialists.
- A mobile or central base hub with upgrade stations.
- Environmental protection modules with temporary low-tech alternatives.
- Simple generated settlement/base tasks.
- Basic power and machine networks.

### Tier 2: Add after the core loop is fun

- Boss/anomaly milestones that alter world state.
- Crew or worker recruitment with passive perks.
- Automation sensors for power, temperature, pressure, doors, pumps, and alarms.
- Morale/stress for NPC workers.
- Events/invasions linked to player actions and world state.
- Ability challenge rooms for movement and tool upgrades.

### Tier 3: Add only if simulation is central

- Gas and liquid flow.
- Temperature exchange and phase changes.
- Contamination/germs/toxins.
- Complex logic gates.
- Multi-base logistics and transport routing.
- Deep worker scheduling and skill specialization.

## Original mechanic directions to distinguish our game

- **Expedition engineering:** hostile zones are solved through portable machines, temporary habitats, drones, and field automation rather than only better armor.
- **Ecology-reactive biomes:** player extraction changes local ecosystems, migration, hazards, and settlement politics.
- **Negotiated settlement networks:** NPC specialists belong to factions with needs, trade routes, rivalries, and ideological preferences.
- **Recoverable disasters:** failures leave scars and new opportunities, such as mutated resources, emergency quests, or altered caves.
- **Blueprint literacy:** players can save, share, and upgrade base-machine layouts in-game as research artifacts.

## Legal and creative boundaries

Use:

- Abstract mechanics and genre conventions.
- Original implementations of crafting, building, simulation, NPC services, progression, and procedural generation.
- New names, visuals, UI, lore, recipes, numbers, enemy archetypes, and balance curves.

Do not use:

- Terraria, Starbound, or Oxygen Not Included names, characters, sprites, music, UI, exact item lists, exact recipes, exact map structures, copied text, or distinctive story elements.
- Exact formulas or hidden mechanics copied as-is from wikis or decompiled data.
- Marketing claims that imply affiliation or compatibility.

## Source notes

- Official Terraria Wiki, `NPCs`: town NPCs, housing, and services context. <https://terraria.wiki.gg/wiki/NPCs>
- Official Terraria Wiki, `Bosses`: boss/event progression and reward context. <https://terraria.wiki.gg/wiki/Bosses>
- Starbounder, `Tier`: threat tiers, planet tiers, environmental protection, gear, merchant stock, and optional story/progression context. <https://starbounder.org/Tier>
- Starbounder, `Cheerful Giraffe`: generated quests, crew recruitment, tech challenge courses, and rail/tech progression context. <https://starbounder.org/Cheerful_Giraffe>
- Starbounder, `Starbound Wiki`: high-level exploration and colonization framing. <https://starbounder.org/Starbound_Wiki>
- Oxygen Not Included Wiki, `Guide/Oxygen`: oxygen consumption and life-support framing. <https://oxygennotincluded.wiki.gg/wiki/Guide/Oxygen>
- Oxygen Not Included Wiki, `Liquid`: liquid behavior, flow, and state context. <https://oxygennotincluded.fandom.com/wiki/Liquid>
- Oxygen Not Included Wiki, `Guide/Temperature Management`: temperature and thermal-management context. <https://oxygennotincluded.wiki.gg/wiki/Guide/Temperature_Management>
- Oxygen Not Included Wiki, `Electrolyzer`: machine input/output and byproduct-chain context. <https://oxygennotincluded.wiki.gg/wiki/Electrolyzer>
- Oxygen Not Included Wiki, `Hidden Mechanics`: example of deeper simulation edge cases to avoid copying exactly. <https://oxygennotincluded.wiki.gg/wiki/Hidden_Mechanics>
