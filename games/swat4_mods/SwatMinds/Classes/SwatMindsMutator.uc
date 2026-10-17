// SwatMinds: emotion-driven suspect action choice + morale/emotion log probe.
// Tracks fear/anger/stress/nerve per suspect and swaps four stock engage
// actions for Mind* subclasses whose selectionHeuristic reads these values.
// GPL, non-commercial.
class SwatMindsMutator extends Engine.Mutator
    config(SwatMinds);

struct Mind
{
    var Pawn  P;
    var float Fear, Anger, Stress, Nerve;
    var float StartMorale;      // first non-zero morale; low morale is measured against it
    var int   LastHealth;
    var float NextProbe;
    var bool  bDown;            // incapacitated/killed already reported
};

var config bool  bEnabled;         // false = stock FRand choice
var config bool  bProbe;           // log one probe line per suspect per ProbeInterval
var config float ProbeInterval;
var config float TickInterval;
var config float NoiseWeight;      // random part added to every score
var config float MoraleFromFear;   // extra morale loss per point of fear from a hit
var config float SeeOfficerRange;
var config float MindWeight;       // 0 = stock score, 1 = emotion score only
var config float AllyFearRange;    // allies within this range (and in sight) feel a hit/down
var config float CloseRange;       // officer this close and in sight = being yelled at / cornered
var config float HearRange;        // allies within this range hear a hit/down through walls
var config float HearFactor;       // heard (not seen) events scare this much of a seen one

var array<Mind> Minds;

function PostBeginPlay()
{
    local SwatMindsMutator Other;

    Super.PostBeginPlay();
    // URL ?Mutator= and ServerActors can both spawn us; keep one
    foreach DynamicActors(class'SwatMindsMutator', Other)
        if (Other != self)
        {
            Destroy();
            return;
        }
    SetTimer(TickInterval, true);
    Log("SwatMinds up: enabled="$bEnabled$" probe="$bProbe, 'SwatMinds');
}

function int FindMind(Pawn P)
{
    local int i;
    for (i = 0; i < Minds.Length; i++)
        if (Minds[i].P == P)
            return i;
    return -1;
}

function int AddMind(Pawn P)
{
    local int i;
    i = Minds.Length;
    Minds.Length = i + 1;
    Minds[i].P = P;
    Minds[i].LastHealth = P.Health;
    Minds[i].Nerve = 0.3 + FRand() * 0.5;
    if (ISwatAI(P).IsAggressive())
        Minds[i].Nerve = FMin(1.0, Minds[i].Nerve + 0.2);
    SwapAbilities(P);
    Log("SwatMinds add "$P.Name$" nerve="$Minds[i].Nerve$" aggressive="$ISwatAI(P).IsAggressive(), 'SwatMinds');
    return i;
}

// Replace the stock engage actions (exact class only, so subclasses such as
// guard variants keep their own behaviour).
function SwapAbilities(Pawn P)
{
    local int i, n;
    local class<Tyrion_ActionBase> C;

    if (P.CharacterAI == None)
        return;
    for (i = 0; i < P.CharacterAI.abilities.Length; i++)
    {
        if (P.CharacterAI.abilities[i] == None)
            continue;
        C = P.CharacterAI.abilities[i].Class;
        if (C == class'SwatAICommon.AttackOfficerAction')
            { P.CharacterAI.abilities[i] = new class<Tyrion_ActionBase>(DynamicLoadObject("SwatMinds.MindAttackOfficerAction", class'Class')); n++; }
        else if (C == class'SwatAICommon.TakeCoverAndAttackAction')
            { P.CharacterAI.abilities[i] = new class<Tyrion_ActionBase>(DynamicLoadObject("SwatMinds.MindTakeCoverAndAttackAction", class'Class')); n++; }
        else if (C == class'SwatAICommon.FleeAction')
            { P.CharacterAI.abilities[i] = new class<Tyrion_ActionBase>(DynamicLoadObject("SwatMinds.MindFleeAction", class'Class')); n++; }
        else if (C == class'SwatAICommon.RegroupAction')
            { P.CharacterAI.abilities[i] = new class<Tyrion_ActionBase>(DynamicLoadObject("SwatMinds.MindRegroupAction", class'Class')); n++; }
    }
    Log("SwatMinds swapped "$n$" abilities on "$P.Name, 'SwatMinds');
}

function bool IsOfficerSide(Actor A)
{
    return A.IsA('SwatOfficer') || A.IsA('SwatPlayer');
}

function Timer()
{
    local Pawn E;
    local Pawn O;
    local int i, Dmg, Seen, Close;
    local float FearAdd, MoraleFrac;
    local CommanderAction CA;

    foreach DynamicActors(class'Pawn', E)
    {
        if (!E.IsA('SwatEnemy'))
            continue;
        i = FindMind(E);
        if (i < 0)
            i = AddMind(E);

        // hits are checked before the conscious filter so one-shot downs count
        Dmg = Minds[i].LastHealth - E.Health;
        Minds[i].LastHealth = E.Health;
        if (Minds[i].bDown)
            continue;
        if (!E.IsConscious() || E.Health <= 0)
        {
            Minds[i].bDown = true;
            Log("SwatMinds down "$E.Name$" dmg="$Dmg$" hp="$E.Health, 'SwatMinds');
            SpreadFear(E, 0.25, "ally down");
            continue;
        }
        if (E.IsCompliant() || ISwatAI(E).IsArrested())
            continue;

        CA = ISwatAI(E).GetCommanderAction();

        // hits: Devastation hide-when-hit numbers (fear +0.1, +0.2 more if dmg > 20)
        if (Dmg > 0)
        {
            FearAdd = 0.1;
            if (Dmg > 20)
                FearAdd += 0.2;
            Minds[i].Fear  = FMin(1.0, Minds[i].Fear + FearAdd * (1.5 - Minds[i].Nerve));
            Minds[i].Anger = FMin(1.0, Minds[i].Anger + 0.25 * Minds[i].Nerve);
            if (bEnabled && CA != None && MoraleFromFear > 0.0)
                CA.ChangeMorale(-FearAdd * MoraleFromFear, "SwatMinds fear");
            Log("SwatMinds hit "$E.Name$" dmg="$Dmg$" fear="$Minds[i].Fear$" anger="$Minds[i].Anger, 'SwatMinds');
            SpreadFear(E, 0.08, "ally hit");
        }

        // stress: officers in sight; close ones also scare (shouting, cornered)
        Seen = 0; Close = 0;
        foreach E.VisibleCollidingActors(class'Pawn', O, SeeOfficerRange)
            if (O != E && IsOfficerSide(O) && O.IsConscious())
            {
                Seen++;
                if (VSize(O.Location - E.Location) < CloseRange)
                    Close++;
            }
        if (Seen > 0)
            Minds[i].Stress = FMin(1.0, Minds[i].Stress + 0.08 * Seen);
        else
            Minds[i].Stress = FMax(0.0, Minds[i].Stress - 0.04);
        if (Close > 0)
            AddFear(i, 0.03 * Close * (1.0 - Minds[i].Nerve));
        // high stress wears down low nerve
        if (Minds[i].Stress > 0.6 && Minds[i].Nerve < 0.5)
            AddFear(i, 0.02);
        // less-lethal effects
        if (ISwatPawn(E).IsFlashbanged() || ISwatPawn(E).IsGassed() || ISwatPawn(E).IsPepperSprayed()
            || ISwatPawn(E).IsStung() || ISwatPawn(E).IsTased())
            AddFear(i, 0.05 * (1.5 - Minds[i].Nerve));

        // decay, with low morale holding fear up
        Minds[i].Fear  = FMax(0.0, Minds[i].Fear - 0.02);
        Minds[i].Anger = FMax(0.0, Minds[i].Anger - 0.015);
        if (CA != None && Minds[i].StartMorale <= 0.0)
            Minds[i].StartMorale = CA.GetCurrentMorale();
        if (CA != None && Minds[i].StartMorale > 0.0)
        {
            MoraleFrac = FClamp(CA.GetCurrentMorale() / Minds[i].StartMorale, 0.0, 1.0);
            Minds[i].Fear = FMax(Minds[i].Fear, (1.0 - MoraleFrac) * 0.5);
        }

        if (bProbe && Level.TimeSeconds >= Minds[i].NextProbe)
        {
            Minds[i].NextProbe = Level.TimeSeconds + ProbeInterval;
            Probe(i, CA, Seen);
        }
    }
}

function AddFear(int i, float Amount)
{
    Minds[i].Fear = FMin(1.0, Minds[i].Fear + Amount);
}

// Allies who can see Victim get scared; low nerve feels it more, high nerve gets angry.
function SpreadFear(Pawn Victim, float Amount, string Why)
{
    local int j;
    local Pawn A;
    local float Dist, K;
    local string How;
    for (j = 0; j < Minds.Length; j++)
    {
        A = Minds[j].P;
        if (A == None || A == Victim || Minds[j].bDown || !A.IsConscious())
            continue;
        Dist = VSize(A.Location - Victim.Location);
        if (Dist <= AllyFearRange && FastTrace(Victim.Location, A.Location))
            { K = 1.0; How = "saw"; }
        else if (Dist <= HearRange)
            { K = HearFactor * (1.0 - 0.5 * Dist / HearRange); How = "heard"; }   // fainter with distance
        else
            continue;
        AddFear(j, Amount * K * (1.5 - Minds[j].Nerve));
        Minds[j].Anger = FMin(1.0, Minds[j].Anger + Amount * K * 0.5 * Minds[j].Nerve);
        Log("SwatMinds feel "$A.Name$" "$How$" "$Why$" ("$Victim.Name$") dist="$int(Dist)$" fear="$Minds[j].Fear$" anger="$Minds[j].Anger, 'SwatMinds');
    }
}

function Probe(int i, CommanderAction CA, int Seen)
{
    local float Morale;
    if (CA != None)
        Morale = CA.GetCurrentMorale();
    Log("SwatMinds probe t="$Level.TimeSeconds$" "$Minds[i].P.Name$" hp="$Minds[i].P.Health$" morale="$Morale
        $" fear="$Minds[i].Fear$" anger="$Minds[i].Anger$" stress="$Minds[i].Stress$" nerve="$Minds[i].Nerve
        $" seen="$Seen$" aggr="$ISwatAI(Minds[i].P).IsAggressive(), 'SwatMinds');
}

// Called by the Mind* actions. Kind: 0 attack, 1 cover, 2 flee, 3 regroup.
function float Score(Pawn P, int Kind, float Stock)
{
    local int i;
    local float F, A, S, N, Base, Result;
    local string KindName;

    if (!bEnabled)
        return Stock;
    i = FindMind(P);
    if (i < 0)
        i = AddMind(P);
    F = Minds[i].Fear; A = Minds[i].Anger; S = Minds[i].Stress; N = Minds[i].Nerve;

    switch (Kind)
    {
        case 0: Base = 0.15 + 0.55 * A + 0.35 * (1.0 - F) * N; KindName = "attack";  break;
        case 1: Base = 0.20 + 0.50 * S + 0.40 * F * N;         KindName = "cover";   break;
        case 2: Base = 0.70 * F * (1.0 - N) + 0.20 * S;        KindName = "flee";    break;
        case 3: Base = 0.40 * F + 0.20 * S;                    KindName = "regroup"; break;
    }
    // blend: stock keeps the situation (cover/escape available), emotion tilts it
    Result = FClamp(Stock * (1.0 - MindWeight) + Base * MindWeight + (FRand() - 0.5) * NoiseWeight, 0.0, 1.0);
    Log("SwatMinds score "$P.Name$" "$KindName$" stock="$Stock$" mind="$Result$" f="$F$" a="$A$" s="$S$" n="$N, 'SwatMinds');
    return Result;
}

static function SwatMindsMutator Get(Actor Any)
{
    local SwatMindsMutator M;
    foreach Any.DynamicActors(class'SwatMindsMutator', M)
        return M;
    return None;
}

defaultproperties
{
    bEnabled=true
    bProbe=true
    ProbeInterval=1.0
    TickInterval=0.25
    NoiseWeight=0.2
    MoraleFromFear=0.25
    SeeOfficerRange=1500.0
    MindWeight=0.5
    AllyFearRange=1200.0
    CloseRange=400.0
    HearRange=3000.0
    HearFactor=0.6
}
