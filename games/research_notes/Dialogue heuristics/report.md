# Dialogue heuristics for judging and editing existing game lines

Scope: Unreal II remixes. No new voiced lines. The only edits are **which lines play, where and when they fire, cuts, trims (cutting an audio file at a clean breath or sentence boundary), reordering, and bark frequency**. A "writer" review step uses these rules to score dialogue on real criteria instead of counting lines.

(Research agent, 2026-10-08. Source caveats: the Ruskin, Firewatch and Hades GDC talks are summarised from session abstracts and secondary write-ups, because the GDC Vault recordings were behind a login limit. The bark cooldown numbers come from a practitioner guide; treat them as starting values to tune. The Chakrabarty 2025 arXiv ID and the Isla Halo 2 talk were cited from memory and not re-checked.)

## Summary

- **Real talk is fast, reactive and economical.** Turn gaps are about 200 ms across languages, every utterance answers something, and people say no more than the situation needs (Grice). Written game dialogue fails when lines explain what both speakers already know or when nobody is reacting to anything. When we can't rewrite, the fix is to *cut and reorder* until each surviving line is a response to something: a previous line, a player action, or something visible.
- **Game dialogue is competing with play.** Portal, Bastion and Left 4 Dead all found the same thing: lines land when they react to what the player just did or can see, and they get ignored or resented when they fire during intense action or repeat. Most of the score should come from **trigger placement, timing and repetition**, which can all be checked mechanically from a transcript plus timing plus location log.
- **Moving lines into a remixed level is the biggest risk.** Each line carries baked-in references to geography, direction, distance, objects and prior events. Every moved line needs a "deixis audit" (checking its this/that/here/there/left/up words) against the new space.
- **AI judgement of dialogue is unreliable in specific, documented ways.** Judges prefer assistant-style, tidy and explicit text, agree with humans at near-random levels on natural multi-party dialogue, can't hear delivery, and inflate scores. Use the LLM for **mechanical checks and quote-backed flagging**, not final taste. Any line that stays because of its delivery needs a human listening pass.

## Rules

Check tags: **[MECH]** can be checked from a transcript plus trigger/timing/location data. **[LLM+Q]** an LLM can flag it but must quote the line as evidence; a human confirms. **[EAR]** needs a human listening in game.

### A. Natural conversation (linguistics)

1. **Every line must answer something.** Each line should be the second half of a pair (an answer, an acknowledgement, a reaction to an event), or a first half that actually gets its second half. Orphan questions and unacknowledged orders feel broken. *Why:* adjacency pairs (Schegloff and Sacks; Sacks, Schegloff and Jefferson 1974); in games, the player's action can be the second part. *Check:* [MECH] tag speech acts; every question or order needs a response line or resolving player action within N seconds; flag orders whose objective is already complete when the line fires.
2. **Keep gaps between turns short** (about 0-500 ms in a scripted exchange). *Why:* Stivers et al. 2009, gaps around 0-200 ms in 10 languages; delays read as trouble. *Check:* [MECH] offsets from sound durations and trigger times; flag gaps over about 1 s within an exchange and unintended overlaps; re-time after trims.
3. **Don't let two voices fight for the same channel.** Priority: story > critical instruction > combat bark > ambient; higher ducks or cancels lower. *Why:* overlap in real talk resolves fast (SSJ 1974); Valve's system picks one response per event and allows interruption (Ruskin 2012). *Check:* [MECH] list overlapping voice intervals; expect zero story/bark overlaps.
4. **Prefer lines that sound spoken over lines that read as written** (short clauses, contractions, fragments, self-corrections, "that"/"there"). *Why:* Biber 1988; self-repair is normal (Schegloff, Jefferson and Sacks 1977). *Check:* [MECH] words per sentence, contraction rate, subordinate clauses; [EAR] final listen.
5. **Quantity: say no more than the moment needs.** Cut sentences that restate the screen, repeat the previous line, or over-detail; trim from the end first. *Why:* Grice's Quantity; Supergiant cut hundreds of Bastion lines. *Check:* [MECH] words per line, content-word overlap with previous line; [LLM+Q] "restates what the player can see" with the quote.
6. **Relevance: the line must be about now** (current goal, location, threat, recent action); lore only in quiet stretches. *Why:* Grice's Relation; Bastion and Hades comment on what the player does. *Check:* [MECH] tag each line's referent; at fire time it must be the active objective, within about 30 m / in view, or within the last about 60 s.
7. **Manner: instructions must be unambiguous** and name things the player can identify here. *Why:* Grice's Manner; Portal's chase where lost players missed GLaDOS. *Check:* [MECH] nouns per directive line must map to a visible actor/landmark from the trigger centre.
8. **Social relationships come through in politeness, not labels.** Protect lines that show how characters treat each other. *Why:* Brown and Levinson 1987. *Check:* [LLM+Q] classify bare order / hedged request / joke with quotes; directness consistent per speaker; [EAR] tone.

### B. Screenwriting and prose craft

9. **No "As you know, Bob."** Cut or move lines telling a listener what they already know; keep the contested or new-listener version. *Check:* [LLM+Q] markers ("as you know", "remember when", "like I told you"), with the quote and the evidence the listener knows.
10. **Subtext beats on-the-nose.** Prefer the implied emotion; cut announced feelings when a nearby line implies them. *Why:* McKee 2016 (dialogue as action); Grice's flouting. *Check:* [LLM+Q] flag self-describing emotion words; a human decides (LLM judges prefer explicit).
11. **Each exchange needs friction or forward motion.** *Why:* McKee, a scene turns a value; Bell, hide exposition in confrontation. *Check:* [LLM+Q] "what is different after it?" with the quoted turning line; none = cut candidate.
12. **Enter late, leave early.** Cut greetings, sign-offs and "over and out" tails unless they carry character. *Check:* [MECH] first/last line under 4 words matching a greeting/sign-off list; trimming an end is a cheap safe edit.
13. **Voices must stay distinct**, identifiable without the subtitle name; don't leave a character with only generic lines. *Check:* [MECH] per-speaker line length, type/token ratio, generic-line share; [EAR] identifiable by ear.

### C. Game-specific

14. **React to what the player just did.** Prefer event triggers over timers; most specific line first. *Why:* Valve's Left 4 Dead rule matching (Ruskin 2012; Valve Response System); Bastion. *Check:* [MECH] share of timer-only triggers; event-to-line latency under 1-2 s.
15. **Don't talk during intense action, or keep it to barks.** Story lines queue until combat clears (3-5 s after the last shot/alert) or drop; only short tactical barks (under about 2 s) in combat. *Why:* Portal's rocket-fight GLaDOS ignored by testers; Firewatch and Valve allow interruption. *Check:* [MECH] join line starts with a combat-state log; report "lines heard in combat".
16. **Repetition budget: cooldowns per line and category**, and no repeat until all alternates are used. Starting values: damage reactions 1-2 s, enemy spotted 5-10 s, ambient 12-20 s, flavour 25-40 s+; story lines once. *Check:* [MECH] per file, minimum/median gap between plays and plays per 10 minutes.
17. **Barks should explain what the AI is doing** and the action should follow. *Why:* F.E.A.R. (Orkin 2006); Halo (Isla 2005). *Check:* [MECH] matching AI state change within about 3 s; flag follow-through under about 70 %.
18. **The voice in your ear must not compete with your eyes.** Radio/companion lines in low-demand moments (after fights, travel, vistas), a few lines per burst, the player keeps control. *Why:* Portal's listening tests and retell checks; Firewatch's walkie-talkie; Half-Life 2's Alyx made to follow. *Check:* [MECH] load score at line start (enemies in range, speed, health trend); [EAR] retell test.
19. **Say only what the player can actually see or do.** Lines must be true at fire time. *Check:* [MECH] precondition list per line, asserted at fire time in an automated run.
20. **Must-hear lines need a safe space, a gate, or a fallback**; lines on a trigger the player can sprint through must be short. *Check:* [MECH] line duration vs the trigger zone's minimum traverse time at sprint/drive speed.
21. **Order matters: cause before comment.** Reactions never before their event; setups before reveals; "like I said" after its line on every route. *Check:* [MECH] dependency graph, reachability check on every route.

### D. Remixed and rebuilt levels

22. **Audit every word that points at something** ("here", "there", "this", "up", "down", "left", "behind you", "the next room", "just ahead", distances, floors). *Why:* deixis takes its meaning from the speaker's location. *Check:* [MECH] regex for deixis words; verify the same relation from the new trigger point.
23. **Re-validate named geography and objects** (rooms, landmarks, vehicles, doors, NPCs exist, recognisable, in view or reach). *Check:* [MECH] noun-to-actor map per line; fail if missing or outside the trigger's radius/view.
24. **Re-validate the story state the line assumes** ("now that the generator's down"). *Check:* [MECH] the rule 21 graph rebuilt from the new map's wiring; every precondition met on all paths.
25. **Keep the story spine; cut the connective tissue first:** ambient/flavour, then redundant directions, then repeated exposition; never a beat line others depend on. *Check:* [MECH] rank by dependants; protect beat lines.
26. **Re-pace lines to the new travel time.** Traversal time at normal pace >= line duration plus gaps, or split the conversation across 2-3 triggers at natural pauses. *Check:* [MECH] segment travel time / summed line duration; flag below 1.0.
27. **Check the ambient sound at the new location** (indoor/radio feel in a big outdoor space; masking by machinery). *Check:* [MECH] ambient-sound loudness near the trigger; [EAR] listen in place.

## Scoring rubric (1 / 3 / 5 anchors)

The reviewer must quote the line ID or text and the log evidence for every score below 5; a score with no quote doesn't count.

| Criterion | 1 (bad) | 3 (acceptable) | 5 (good) | Check |
|---|---|---|---|---|
| **1. Truth to the world** (19, 22-24) | 2+ lines refer to things that aren't there, wrong direction, or already happened | Referents exist; 1-2 directions/distances vague or slightly off | Every pointing word and named object checks out from the trigger point; no stale preconditions | MECH |
| **2. Timing vs play load** (15, 18, 20, 26) | Story/radio lines play during combat or get cut off on zone exit | No story in combat; some bunching or late reactions | Story lands in quiet stretches; must-hear lines can't be missed; reactions within 1-2 s | MECH |
| **3. Repetition** (16) | Same file twice within 30 s, or a story line repeats | Occasional in-window bark repeats (under 5 % of plays) | No file repeats within its window; alternates rotate; story once | MECH |
| **4. Reactivity / relevance** (1, 6, 14, 17) | Mostly timer/volume chatter unrelated to play; barks announce things that don't happen | About half of lines tie to a current event/objective | Nearly every line answers an event, a line or a visible thing; intent barks followed through >= 70 % | MECH + LLM+Q |
| **5. Economy** (5, 9, 12, 25) | Restating the screen, "as you know", long greetings/sign-offs | Some padding; every exchange has a point | Starts late, ends on the strongest line; nothing restates the visible | LLM+Q, human confirms |
| **6. Exchange quality** (2, 3, 11) | Gaps of 1 s+, voices clash, pure-agreement exchanges | Clean turn-taking; some exchanges change nothing | Tight gaps, no clashes, each exchange turns something | MECH (timing) + LLM+Q |
| **7. Voice and performance** (4, 8, 10, 13) | Speakers interchangeable; deliveries flat or out of place | Mostly distinct; 1-2 deliveries off in the new place | Identifiable by ear; performances fit the new space and mood | **EAR only** |

Criteria 1-4 are mechanical (automate, run every build). 5-6 can be pre-screened by an LLM, a human confirms. 7 is human only; the LLM must not score it.

## AI judgement pitfalls (and mitigations)

What goes wrong:
1. **Preference for assistant-style speech.** On natural multi-party dialogue, LLM judges agreed with humans near random (Cohen's kappa about 0.11-0.17) and acted as style detectors, even preferring GPT-like conversations with shuffled turns (Samanta et al. 2026). An LLM will tend to score the tidy, explicit line above the clipped, subtext-heavy one that sounds real.
2. **Length and leniency bias.** Verbosity bias (Saito et al. 2023; direction varies by model, Judging the Judges 2026); scores crowd the top of subjective scales; position, verbosity and self-enhancement biases (Zheng et al. 2023).
3. **Cliché and exposition blindness.** Expert writers find AI prose full of cliché and unnecessary exposition (Chakrabarty et al. 2023, 2025); a model that writes that way is poorly placed to penalise it.
4. **No ear.** A transcript can't carry timing, pauses, overlap, intent, sarcasm, mixing or masking.
5. **No body in the space.** The model doesn't feel player load, sightlines or travel time; those must come from logs.
6. **Bias toward keeping things and rewriting.** We can't rewrite, so "rephrase" suggestions are out of scope.

Mitigations:
- **Mechanical first:** rules 1-3, 7, 12, 14-17, 19-26 as scripts; the LLM reads the reports and points at problems.
- **Concrete anchors:** the 1/3/5 rubric, with good and bad anchor examples from Unreal II's own lines.
- **Quote or it doesn't count.** Reject unquoted scores.
- **Binary, local questions** ("does this line refer to an object not within 30 m?") over "is this good?".
- **Shuffle and swap** when comparing alternatives; discard verdicts that flip.
- **No style scoring by the LLM:** criterion 7 and the last word on rules 4, 10, 13 belong to a human.
- **Human listening pass** before shipping: play once with subtitles off and note lines that are unclear, badly timed, false to the screen, or heard twice; then the retell test (Portal's method).

## Sources

Conversation and pragmatics
- Sacks, Schegloff and Jefferson (1974), "A Simplest Systematics for the Organization of Turn-Taking for Conversation", *Language* 50. https://muse.jhu.edu/article/452679/summary
- Stivers et al. (2009), "Universals and cultural variation in turn-taking in conversation", *PNAS*. https://emcawiki.net/Stivers-etal2009 ; timing review: https://pmc.ncbi.nlm.nih.gov/articles/PMC4586330
- Schegloff, Jefferson and Sacks (1977), "The Preference for Self-Correction in the Organization of Repair in Conversation", *Language* 53.
- Grice (1975), "Logic and Conversation"; SEP "Implicature": https://plato.stanford.edu/archives/spr2014/entries/implicature/ ; Potts handout: https://web.stanford.edu/~cgpotts/teaching/2011-2012/236/materials/ling236-handout-04-02-implicature.pdf
- Brown and Levinson (1987), *Politeness*. https://en.wikipedia.org/wiki/Politeness_theory
- Biber (1988), *Variation across Speech and Writing*.

Craft
- McKee (2016), *Dialogue*. https://www.publishersweekly.com/9781455591916
- TV Tropes, "As You Know". https://tvtropes.org/pmwiki/pmwiki.php/Main/AsYouKnow
- J. S. Bell, "Hide exposition inside confrontation". https://killzoneblog.com/2023/07/hide-exposition-inside-confrontation.html
- Writing Excuses on exposition. https://writingexcuses.com/?p=13576

Game dialogue
- Ruskin (2012), "AI-driven Dynamic Dialog through Fuzzy Pattern Matching", GDC. https://www.gdcvault.com/play/1015528/AI-driven-Dynamic-Dialog-through ; http://assemblyrequired.crashworks.org/2012/03/13/ai-driven-dynamic-dialog-at-gdc-2012/ ; https://emshort.blog/2012/03/16/gdc-2012-talk-on-dynamic-dialogue/
- Valve Developer Community, "Response System". https://developer.valvesoftware.com/wiki/Response_System
- Ewing and Armstrong (2017), "Do You Copy? Dialog Systems and Tools in Firewatch", GDC. https://gdconf.com/news/come-gdc-2017-hear-firewatchs-unique-dialog-system-works
- Kasavin and Korb (2021), "Breathing Life into Greek Myth: The Dialogue of Hades", GDC. https://gdcvault.com/play/1026975/Breathing-Life-into-Greek-Myth ; https://www.screenhub.com.au/news-article/features/digital/jini-maxwell/hades-greg-kasavin-breaks-down-supergiants-unique-approach-to-narrative-262459
- Bastion narration (Kasavin): https://www.supergiantgames.com/blog/in-depth-writing-bastion/ ; https://gamebanshee.com/86p4
- Portal GDC postmortem: https://www.gamedeveloper.com/game-platforms/best-of-gdc-the-secrets-of-i-portal-i-s-huge-success ; https://www.shacknews.com/article/51474/gdc-08-portal-creators-on
- Portal 2 scene timing: https://wiki.portal2.sr/Bridge_The_Gap
- Orkin (2006), "Three States and a Plan: The AI of F.E.A.R.". https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf
- Isla (2005), "Handling Complexity in the Halo 2 AI" (not re-checked).
- Half-Life 2 commentary: https://combineoverwiki.net/wiki/Commentary_notes ; https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2:_Episode_Two
- Repetition: https://soundingames.dei.uc.pt/index.php/Requisite_Variety ; bark cooldowns: https://pulsegeek.com/articles/dialogue-barks-timing-and-cooldown-best-practices/

AI judgement
- Samanta et al. (2026), "Style over Substance: LLM-as-a-Judge Fails to Evaluate Multi-Party Social Dialogue", ICLR. https://iclr.cc/virtual/2026/10014636 ; https://preview.aclanthology.org/ingest-acl/2026.acl-long.2006/
- Saito et al. (2023), "Verbosity Bias in Preference Labeling by Large Language Models". https://arxiv.org/pdf/2310.10076
- Zheng et al. (2023), "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena". https://arxiv.org/abs/2306.05685
- "Judging the Judges" (2026). https://arxiv.org/pdf/2604.23178
- Chakrabarty et al. (2023), "Art or Artifice?". https://arxiv.org/pdf/2309.14556
- Chakrabarty et al. (2025), "Can AI writing be salvaged?". https://arxiv.org/abs/2409.14509 (from memory; verify)
- Shortcut bias in LLM judges. https://arxiv.org/html/2602.07996v1
