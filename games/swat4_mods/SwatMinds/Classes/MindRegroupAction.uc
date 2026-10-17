// SwatMinds: RegroupAction whose choice score comes from the suspect's emotions.
// Stock eligibility is kept: if the stock heuristic says 0 (cannot do it), so do we.
class MindRegroupAction extends SwatAICommon.RegroupAction
    config(AI);

var SwatMindsMutator Minds;

function float selectionHeuristic( AI_Goal goal )
{
    local float Stock;
    local Pawn P;

    Stock = Super.selectionHeuristic(goal);
    if (Stock <= 0.0 || goal == None || AI_CharacterResource(goal.resource) == None)
        return Stock;
    P = AI_CharacterResource(goal.resource).m_pawn;
    if (P == None)
        return Stock;
    if (Minds == None)
        Minds = class'SwatMindsMutator'.static.Get(P);
    if (Minds == None)
        return Stock;
    return Minds.Score(P, 3, Stock);
}
