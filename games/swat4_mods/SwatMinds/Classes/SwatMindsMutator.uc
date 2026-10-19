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
    var float NextSay;          // comms: this suspect may speak again after this time
    var float RuleTime[8];      // comms: per-rule memory (last time each rule fired)
    var bool  bFearSaid, bAngerSaid; // threshold lines fire once per crossing
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
var config bool  bRandomInstantAction; // after each map load, store a random other mission as "last played"

var config bool  bComms;           // suspect callouts from stock recorded lines
var config float SayCooldown;      // per suspect
var config float SayGap;           // between any two suspects
var config float RuleCooldown;     // same rule, same suspect

var array<Mind> Minds;
var array<Pawn> DownOfficers;
var float LastSay;

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
    if (bRandomInstantAction)
        RandomizeInstantAction();
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
    local int k;
    local bool bKnown;

    // officer-down tracking (each officer reacts once per down)
    foreach DynamicActors(class'Pawn', O)
    {
        if (!IsOfficerSide(O) || (O.IsConscious() && O.Health > 0))
            continue;
        bKnown = false;
        for (k = 0; k < DownOfficers.Length; k++)
            if (DownOfficers[k] == O)
                bKnown = true;
        if (!bKnown)
        {
            DownOfficers[DownOfficers.Length] = O;
            OfficerDown(O);
        }
    }

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

        // comms: threshold crossings (re-arm below a lower mark)
        if (Minds[i].Fear >= 0.7 && !Minds[i].bFearSaid)
            Minds[i].bFearSaid = Say(i, 4);
        else if (Minds[i].Fear < 0.4)
            Minds[i].bFearSaid = false;
        if (Minds[i].Anger >= 0.6 && !Minds[i].bAngerSaid)
            Minds[i].bAngerSaid = Say(i, 5);
        else if (Minds[i].Anger < 0.3)
            Minds[i].bAngerSaid = false;

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
        // trace eye to chest/eye: pawn centres sit inside props and downed bodies (0 "saw" in playtest 4)
        if (Dist <= AllyFearRange && (FastTrace(Victim.Location + vect(0,0,40), A.Location + vect(0,0,1) * A.BaseEyeHeight)
                                   || FastTrace(Victim.Location + vect(0,0,1) * Victim.BaseEyeHeight, A.Location + vect(0,0,1) * A.BaseEyeHeight)))
            { K = 1.0; How = "saw"; }
        else if (Dist <= HearRange)
            { K = HearFactor * (1.0 - 0.5 * Dist / HearRange); How = "heard"; }   // fainter with distance
        else
            continue;
        AddFear(j, Amount * K * (1.5 - Minds[j].Nerve));
        Minds[j].Anger = FMin(1.0, Minds[j].Anger + Amount * K * 0.5 * Minds[j].Nerve);
        Log("SwatMinds feel "$A.Name$" "$How$" "$Why$" ("$Victim.Name$") dist="$int(Dist)$" fear="$Minds[j].Fear$" anger="$Minds[j].Anger, 'SwatMinds');
        // comms rules, most specific first; Say() refuses on cooldown and the next rule is not tried
        if (Why == "ally down" && How == "saw" && Minds[j].Fear >= 0.5)
            Say(j, 0);
        else if (Why == "ally down" && How == "saw" && Minds[j].Anger > Minds[j].Fear)
            Say(j, 1);
        else if (Why == "ally down")
            Say(j, 2);
        else if (Minds[j].Fear >= 0.4)
            Say(j, 3);
    }
}

// Comms v1 (Ruskin dynamic-dialog style, research/l4d-ai-talk.md): rules pick a stock
// recorded enemy line; memory = per-suspect, per-rule and global cooldowns.
// 0 saw ally down + scared: scream     1 saw ally down + angry: defiant
// 2 ally down (heard/other): call help 3 ally hit + scared: call help
// 4 fear crossed 0.7: flee line        5 anger crossed 0.6: defiant
// 6 officer down nearby: downed-officer reaction
function bool Say(int i, int Rule)
{
    local EnemySpeechManagerAction SM;
    local string Line;
    local float T;

    if (!bComms || Minds[i].P == None)
        return false;
    T = Level.TimeSeconds;
    if (T < Minds[i].NextSay || T < LastSay + SayGap
        || (Minds[i].RuleTime[Rule] > 0.0 && T < Minds[i].RuleTime[Rule] + RuleCooldown))
        return false;
    SM = EnemySpeechManagerAction(ISwatAI(Minds[i].P).GetSpeechManagerAction());
    if (SM == None)
        return false;
    switch (Rule)
    {
        case 0: SM.TriggerScreamSpeech();          Line = "Scream";        break;
        case 1: SM.TriggerUncompliantSpeech();     Line = "NonCompliant";  break;
        case 2: SM.TriggerCallForHelpSpeech();     Line = "CalledForHelp"; break;
        case 3: SM.TriggerCallForHelpSpeech();     Line = "CalledForHelp"; break;
        case 4: SM.TriggerFleeSpeech();            Line = "Flee";          break;
        case 5: SM.TriggerUncompliantSpeech();     Line = "NonCompliant";  break;
        case 6: SM.TriggerDownedOfficerSpeech();   Line = "DownOfficer";   break;
    }
    Minds[i].NextSay = T + SayCooldown;
    Minds[i].RuleTime[Rule] = T;
    LastSay = T;
    Log("SwatMinds say "$Minds[i].P.Name$" rule="$Rule$" line="$Line$" fear="$Minds[i].Fear$" anger="$Minds[i].Anger, 'SwatMinds');
    return true;
}

// Officer went down: the nearest conscious suspect who can see (or else hear) it reacts.
function OfficerDown(Pawn O)
{
    local int j, Best;
    local float Dist, BestDist;
    local bool bSeen, bBestSeen;

    Best = -1;
    for (j = 0; j < Minds.Length; j++)
    {
        if (Minds[j].P == None || Minds[j].bDown || !Minds[j].P.IsConscious())
            continue;
        Dist = VSize(Minds[j].P.Location - O.Location);
        if (Dist > HearRange)
            continue;
        bSeen = FastTrace(O.Location + vect(0,0,40), Minds[j].P.Location + vect(0,0,1) * Minds[j].P.BaseEyeHeight);
        if (Best < 0 || (bSeen && !bBestSeen) || (bSeen == bBestSeen && Dist < BestDist))
            { Best = j; BestDist = Dist; bBestSeen = bSeen; }
    }
    Log("SwatMinds officer down "$O.Name$" reactor="$Best, 'SwatMinds');
    if (Best >= 0)
    {
        Minds[Best].Anger = FMin(1.0, Minds[Best].Anger + 0.2);
        Say(Best, 6);
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

// Instant Action replays SwatGUIConfig.LastMissionPlayed*, saved by GameStart() just
// before this map loaded. Overwrite it with a random other campaign mission so the
// next Instant Action click goes somewhere new. The fields are private: SetPropertyText.
function RandomizeInstantAction()
{
    local SwatRepo Repo;
    local SwatGUIConfig Cfg;
    local int k, n, Tries;
    local string Cur;

    // the local PlayerController does not exist yet in PostBeginPlay; the Repo does
    Repo = SwatRepo(Level.GetRepo());
    if (Repo == None || Repo.GuiConfig == None)
    {
        Log("SwatMinds instant action: no Repo/GuiConfig", 'SwatMinds');
        return;
    }
    Cfg = Repo.GuiConfig;
    n = Min(Cfg.MissionName.Length, Cfg.FriendlyName.Length);
    if (n < 2)
        return;
    Cur = string(Level.Outer.Name);       // map package, e.g. SP-FoodWall
    do
        k = Rand(n);
    until (string(Cfg.MissionName[k]) != Cur || ++Tries > 10);
    Cfg.SetPropertyText("LastMissionPlayedName", string(Cfg.MissionName[k]));
    Cfg.SetPropertyText("LastMissionPlayedFriendlyName", Cfg.FriendlyName[k]);
    Cfg.SetPropertyText("LastMissionPlayedCustomScenario", "None");
    Cfg.SaveConfig();
    Log("SwatMinds instant action next: "$Cfg.MissionName[k]$" (this map "$Cur$")", 'SwatMinds');
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
    bRandomInstantAction=true
    bComms=true
    SayCooldown=6.0
    SayGap=2.0
    RuleCooldown=20.0
}
