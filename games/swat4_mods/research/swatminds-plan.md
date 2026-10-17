# SwatMinds plan: tactical AI + communication (10-17)

Sources: tactical-fps-ai.md (survey, ranked ideas), ai-communication.md (barks + SDK speech hooks), breach-cover-ai.md (CQB, officers covering the player), l4d-ai-talk.md (pending).

Key hook (verified in SDK): `ISwatAI(p).GetSpeechManagerAction().TriggerSpeech('<Event>')` (ISwatAI.uc:146, CharacterSpeechManagerAction.uc:19). Stock recorded lines only; unknown event names play nothing.

## Build order (fun per effort)
1. **Comms v1 (suspects).** Fire stock events on SwatMinds state changes: hit -> ReactedInjury*, down -> ReactedDown, flee -> AnnouncedFlee, cover under fire -> CalledForHelp, nerve break -> AnnouncedCompliant. 4 s per-pawn cooldown, one speaker per 3000-unit group. Heard callouts change state: CalledForHelp raises listener stress and makes them aware; flee/down raises fear (capped).
2. **Response curves.** Move the score formulas into small configurable curves (Dave Mark), so items 3-6 are only data.
3. **Surrender curve.** Surrender/Flee scaled by fear, nerve, outnumbered, ally down nearby, stun.
4. **Leader panic/rally.** Highest-nerve suspect is leader; their down drops nearby nerve, alive leader rallies.
5. **Suppression.** Near misses raise fear and cut attack; push to cover.
6. **Officer comms + cover.** Officer reports (ReportedOfficerDown, ReportedMaleSuspectFleeing, ReportedSuspectNeutralized) via ElementSpeechManagerAction; nearest officer covers the player when a suspect has sight of them (Hive.uc:460 engage point).
7. Later: feign surrender ambush, alertness ladder + investigate, role tags, suspect position picking.
