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

var config string LiveFile;        // hot knobs: console script re-run while the level plays ("" = off)
var config float  LiveInterval;
var float NextLive;
var config bool  bEarlyExit;       // gym 10-23: quit at a 30 s tally once the game is decided (all suspects down/arrested + hostages secured, or an officer down)
var int TallyFree, TallyOff, TallyHostLeft, TallyHS, PrevHS;
var config float  ExitAfter;       // gym: final tally + clean quit at this level time (0 = off); each live exec costs ~6-9 s wall, so the gym execs once
var bool bExiting;
var bool bIADone;
var string IAPick, IAPickFriendly;   // chosen next instant-action map; re-applied because the GUI saves the current map again later              // instant-action pick written (after GameStart's SaveLastMissionPlayed)
var config bool  bAutoOfficers;    // officers pick their own squad orders (no player commands)
var config float OfficerThink;     // seconds between officer decisions
var config float MaxDoorDist;      // only doors this close to the squad
var float NextOfficerThink;
var float OfficersReadyAt;
var config bool  bEscort;          // officers stay with the player (FallIn) and hold a 360 perimeter instead of clearing doors (playtest 5 wish)
var array<AimAtPointGoal> SectorGoals;
var array<Pawn> SectorPawns;
var array<float> SectorPosted;
var string SectorSig;
var array<Pawn> TrainPawns;        // this tick's column order (front to tail)
var array<int> TrainYaw;           // world yaw of each officer's sector
// escort "bubble" (10-21): loose group around the player, each officer picks guard / secure / evidence
var config bool  bBubble;
var config float BubbleThink, BubbleMin, BubbleMax, SecureRange;
var array<Pawn> BubPawn;
var array<byte> BubTask;           // 0 guard, 1 restrain, 2 evidence
var array<Actor> BubTarget;
var array<vector> BubPt, BubMovePt;
var array<float> BubNext, BubBiasT, BubAimT, BubMoveT;
var array<int> BubBias;            // own random bearing around the player
var array<MoveToLocationGoal> BubMove;
var array<AimAtPointGoal> BubAim;
var array<RestrainAndReportGoal> BubRR;
var array<SecureEvidenceGoal> BubSE;
var array<Actor> BubEvid;
var array<int> BubOld;             // oldest unpainted threat navs this tick
var float BubThreatT, BubEvidT;
var int BubSecN, BubEvN;
// coverage "paint" scorer (10-20): nav points the squad can see are threats; aim cone + LOS paints them
var config bool  bPaint;
var config float PaintRange, PaintFade, PaintCone, DeadHold;
var array<NavigationPoint> PaintNav;
var array<float> PaintTime;
var array<byte> PaintThreat;
var array<int> ThreatIdx;
var bool bPaintInit;
var float PaintShare, PaintSum, NextPaintLog;
var int PaintN;
var array<vector> SqEye, SqDir;
var vector SqC;
var array<Pawn> DeadPawns;         // dead-space hold per officer
var array<int> DeadIdx;
var array<float> DeadUntil;
// halt: cover spots + shoulder tap
var config bool  bCoverHold;
var config float CoverSearch, TapGap, HaltTime;
var vector HaltLoc;
var float HaltSince, TapSum;
var int TapN;
var bool bTapDone, bCoverDone;
var array<MoveToLocationGoal> CoverGoals;
var array<Pawn> CoverPawns;
var array<vector> CoverPts;
var array<float> CoverPosted;
// director (live feature + gym probe): sends a threat from the least-painted out-of-sight spot
var config bool  bDirector;
var config float DirectorInterval, DirectorRange, DirectorMin, DirectorTimeout;
var float NextDirector, DirStart, DirSeenAt, DirFaceSum;
var int DirN, DirMiss, DirNoShow;
var Pawn DirPawn;
var vector DirPt;
var MoveToLocationGoal DirGoal;
var array<Door> UsedDoors;
var array<Pawn> SecureAsked;
var float NextOfficerWhy;
var float LastOrderTime;
var Door LastOrderDoor;
var config float OrderTimeout;
// 10-20 c ROE (hard rule, b2studios lesson): stock officers attack a suspect the moment it becomes a threat (aims once;
// SwatEnemy.bThreat is private native and never resets, SetPropertyText cannot clear it). For the first ComplyWait s of a
// threat, every AI officer in sight gets an OrderComplianceGoal (weapon resource, pri 85 > AttackTargetGoal 80): it shouts
// instead of firing. The hold ends at once when the suspect fires (ammo in clip drops). 0 = stock.
var config float ComplyWait;
var array<Pawn> CwPawn;
var array<int> CwRounds;           // rounds left in the suspect's clip last tick (-1 = no fired weapon)
var array<float> CwSince;          // first tick seen as a threat (0 = not yet)
var array<byte> CwFired, CwHeld, CwDone;
var array<Pawn> HoldO, HoldE;
var array<OrderComplianceGoal> HoldG;
var int CwHold, CwShot, CwComply;
var config bool bGhostPlayer;
var config bool  bScoreDoors;      // officers pick doors by intel (heard/seen suspects) instead of nearest
var config float IntelW;           // score bonus for a door with intel behind it (1.0 = worth 1000 uu of walking)
var config float IntelRange;       // intel this close behind a door counts
var config float IntelLife;        // seconds intel stays fresh
var array<vector> IntelLoc;
var array<float> IntelTime;
var int Orders;
var float NextTally;
var config float Dilation;         // >0: force Level.TimeDilation (gym speed-up)
var config bool  bAutoSpeed;        // gym: retune Level.TimeDilation so level time keeps up with wall time
var config float SpeedTarget;       // wanted level s per wall s (1 = real time)
var config float MaxDilation;
var float SpeedW0, SpeedT0;
var config bool bClockProbe;       // log dt/level time/wall every 200 frames (gym speed check)
var int Frames;                    // Tick count, for fps= in the tally line
var string LastLive;
var config bool  bTraj;            // log one "traj" line of all pawn positions every TrajInterval (gym demos/data)
var config float TrajInterval;
var float NextTraj;
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
    Log("SwatMinds url "$Level.GetLocalURL()$" game="$Level.Game, 'SwatMinds');
    // gym runner: ?SMLive=<file> gives each parallel instance its own hot-knob script
    if (Level.Game != None && Level.Game.ParseOption(Mid(Level.GetLocalURL(), InStr(Level.GetLocalURL(), "?")), "SMLive") != "")
    {
        LiveFile = Level.Game.ParseOption(Mid(Level.GetLocalURL(), InStr(Level.GetLocalURL(), "?")), "SMLive");
        Log("SwatMinds live file "$LiveFile, 'SwatMinds');
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
    local EnemyCommanderAction ECA;
    local PlayerController PC;
    local string R;
    local Pawn O;

    local int i, Dmg, Seen, Close;
    local float FearAdd, MoraleFrac;
    local CommanderAction CA;
    local int k;
    local bool bKnown;
    // GameStart() saves this map as last played after PostBeginPlay, so pick the next one a few seconds in
    if (bRandomInstantAction && !bIADone && Level.TimeSeconds > 3.0)
    {
        bIADone = true;
        RandomizeInstantAction();
    }
    else if (bIADone)
        ReapplyInstantAction();

    if (Dilation > 0 && Level.TimeDilation != Dilation)
        Level.TimeDilation = Dilation;

    // hot knobs: re-run the console script (`set <class> <prop> <value>` lines), then log what live objects hold
    if (LiveFile != "" && Level.TimeSeconds >= NextLive)
    {
        NextLive = Level.TimeSeconds + LiveInterval;
        PC = Level.GetLocalPlayerController();
        if (PC != None)
            R = PC.ConsoleCommand("exec "$LiveFile);
        else
            R = ConsoleCommand("exec "$LiveFile);
        foreach DynamicActors(class'Pawn', E)
            if (E.IsA('SwatEnemy') && ECA == None)
                ECA = EnemyCommanderAction(ISwatAI(E).GetCommanderAction());
        if (ECA != None)
            R = "HearRange="$HearRange$" MindWeight="$MindWeight$" bComms="$bComms$" | live "$ECA.Name$" HighScream="$ECA.HighSkillScreamChance$" MaxMorale="$ECA.MaxMorale$" | default HighScream="$class'EnemyCommanderAction'.default.HighSkillScreamChance;
        else
            R = "HearRange="$HearRange$" MindWeight="$MindWeight$" bComms="$bComms$" (no enemy yet)";
        if (R != LastLive)
            Log("SwatMinds live "$R, 'SwatMinds');
        LastLive = R;
        E = None;
    }

    if (bPaint && OfficersReadyAt > 0.0 && Level.TimeSeconds >= OfficersReadyAt)
        UpdatePaint();
    if (bAutoOfficers && bEscort && OfficersReadyAt > 0.0 && Level.TimeSeconds >= OfficersReadyAt)
        UpdateSectors();
    if (bDirector && bPaint && OfficersReadyAt > 0.0 && Level.TimeSeconds >= OfficersReadyAt)
        UpdateDirector();
    if (ComplyWait > 0 && OfficersReadyAt > 0.0 && Level.TimeSeconds >= OfficersReadyAt)
        UpdateComply();
    if (bAutoOfficers && Level.TimeSeconds >= NextOfficerThink)
    {
        NextOfficerThink = Level.TimeSeconds + OfficerThink;
        AutoOfficers();
    }
    if (bAutoOfficers && Level.TimeSeconds >= NextTally)
    {
        NextTally = Level.TimeSeconds + 30.0;
        Tally();
        if (bEarlyExit && ExitAfter > 0 && !bExiting && Level.TimeSeconds > 20 && (TallyOff > 0 || (TallyFree == 0 && (TallyHostLeft == 0 || TallyHS == PrevHS))))
        {
            if (TallyOff > 0) SideLog("SwatMinds early end t="$int(Level.TimeSeconds)$" why=offDown");
            else SideLog("SwatMinds early end t="$int(Level.TimeSeconds)$" why=clear");
            ExitAfter = Level.TimeSeconds;  // the exit block below tallies again and quits this tick
        }
    }
    if (ExitAfter > 0 && Level.TimeSeconds >= ExitAfter && !bExiting)
    {
        bExiting = true;
        Tally();
        SideLog("SwatMinds exit t="$int(Level.TimeSeconds));
        PC = Level.GetLocalPlayerController();
        if (PC != None)
            PC.ConsoleCommand("exit");
        else
            ConsoleCommand("exit");
    }
    if (bTraj && Level.TimeSeconds >= NextTraj)
    {
        NextTraj = Level.TimeSeconds + TrajInterval;
        Traj();
    }

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
    AddIntel(Minds[i].P.Location, "say "$Minds[i].P.Name);
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
// Auto officers v1: the stock element squad gets its orders from here instead of the player.
// Order of goals: secure compliant people > clear the nearest unused door. Uses the same
// OfficerTeamInfo calls the command menu makes, so all stock squad behaviour is kept.
function AddIntel(vector L, string Why)
{
    local int k;
    for (k = 0; k < IntelLoc.Length; k++)
        if (VSize(IntelLoc[k] - L) < 200.0)
        {
            IntelLoc[k] = L; IntelTime[k] = Level.TimeSeconds;
            return;
        }
    IntelLoc[IntelLoc.Length] = L;
    IntelTime[IntelTime.Length] = Level.TimeSeconds;
    Log("SwatMinds intel "$Why$" at "$int(L.X)$","$int(L.Y), 'SwatMinds');
}

// 1 if fresh intel lies on the far side of door D, as seen from L
function int IntelBehind(Door D, vector L)
{
    local int k;
    for (k = 0; k < IntelLoc.Length; k++)
        if (Level.TimeSeconds - IntelTime[k] < IntelLife && VSize(IntelLoc[k] - D.Location) < IntelRange
            && ((IntelLoc[k] - D.Location) Dot (L - D.Location)) < 0)
            return 1;
    return 0;
}

function float WallNow()
{
    return Level.Hour*3600 + Level.Minute*60 + Level.Second + Level.Millisecond/1000.0;
}

event Tick(float DeltaTime)
{
    local float W, S;
    Frames++;
    if (bGhostPlayer && Level.Pauser != None)  // gym: WinDrv pauses a slot whose window loses focus; bAlwaysTick keeps this running
    {
        SideLog("SwatMinds unpause t="$int(Level.TimeSeconds));
        Level.Pauser = None;
    }
    if (bAutoSpeed)
    {
        W = WallNow();
        if (SpeedW0 == 0 || W < SpeedW0) { SpeedW0 = W; SpeedT0 = Level.TimeSeconds; }
        else if (W - SpeedW0 >= 3.0)
        {
            S = (Level.TimeSeconds - SpeedT0) / (W - SpeedW0);  // level s per wall s at the current dilation
            if (S > 0)
                Level.TimeDilation = FClamp(Level.TimeDilation * SpeedTarget / S, 1.0, MaxDilation);
            SpeedW0 = W; SpeedT0 = Level.TimeSeconds;
        }
    }
    if (bClockProbe && Frames % 200 == 0)
        SideLog("SwatMinds clock frames="$Frames$" dtms="$int(DeltaTime*1000000)/1000.0$" dil="$Level.TimeDilation$" t="$Level.TimeSeconds$" wall="$(Level.Hour*3600+Level.Minute*60+Level.Second)$"."$Level.Millisecond$" pauser="$Level.Pauser);
    Super.Tick(DeltaTime);
}

function Tally()
{
    local Pawn P;
    local int SD, SA, HS, OD, SL, HL;
    local string R;
    foreach DynamicActors(class'Pawn', P)
    {
        if (P.IsA('SwatEnemy'))
        {
            if (!P.IsConscious()) SD++;
            else if (ISwatAI(P).IsArrested()) SA++;
            else SL++;
        }
        else if (P.IsA('SwatHostage') && ISwatAI(P).IsArrested())
            HS++;
        else if (P.IsA('SwatHostage') && P.IsConscious())
            HL++;
        else if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer') && !P.IsConscious())
            OD++;
    }
    R = "SwatMinds tally t="$int(Level.TimeSeconds)$" score="$bScoreDoors$" orders="$Orders$" susDown="$SD$" susArrest="$SA$" susFree="$SL$" hostSecured="$HS$" offDown="$OD$" intel="$IntelLoc.Length$" wall="$(Level.Hour*3600+Level.Minute*60+Level.Second)$"."$Level.Millisecond$" frames="$Frames$" dil="$Level.TimeDilation
        $" paint="$(PaintSum / Max(1, PaintN))$" tap="$(TapSum / Max(1, TapN))$" tapN="$TapN$" dirFace="$(DirFaceSum / Max(1, DirN))$" dirN="$DirN$" dirMiss="$DirMiss$" dirNoShow="$DirNoShow$" cwHold="$CwHold$" cwShot="$CwShot$" cwComply="$CwComply$" hostLeft="$HL;
    PrevHS = TallyHS; TallyFree = SL; TallyOff = OD; TallyHostLeft = HL; TallyHS = HS;
    SideLog(R);
}

// log line + gym side file (closed after every write so a killed gym slot keeps it; the main log is buffered)
function SideLog(string R)
{
    local FileLog FL;
    Log(R, 'SwatMinds');
    if (LiveFile != "")
    {
        FL = Spawn(class'FileLog');
        if (FL != None)
        {
            FL.OpenLog("SMTally_"$Left(LiveFile, InStr(LiveFile$".", ".")));
            FL.Logf(R);
            FL.CloseLog();
            FL.Destroy();
        }
    }
}

// one line per TrajInterval: <kind><n>:x,y,yaw,state for every officer (O), suspect (E), hostage (H); state c=free a=arrested d=down
function Traj()
{
    local Pawn P;
    local string S, K, St;
    local int nO, nE, nH;
    foreach DynamicActors(class'Pawn', P)
    {
        if (P.IsA('SwatEnemy')) { K = "E"$nE; nE++; }
        else if (P.IsA('SwatHostage')) { K = "H"$nH; nH++; }
        else if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer')) { K = "O"$nO; nO++; }
        else continue;
        if (!P.IsConscious()) St = "d";
        else if (ISwatAI(P).IsArrested()) St = "a";
        else St = "c";
        S = S$" "$K$":"$int(P.Location.X)$","$int(P.Location.Y)$","$(P.Rotation.Yaw & 65535)$","$St;
    }
    Log("SwatMinds traj t="$int(Level.TimeSeconds * 10) / 10.0$" orders="$Orders$S, 'SwatMinds');
}

function AutoOfficers()
{
    local OfficerTeamInfo Squad;
    local PlayerController PC;
    local Pawn Giver, Lead, P, Best;
    local Door D, BestDoor;
    local float Dist, BestDist;
    local int k;
    local bool bUsed;
    local string Cmd;
    local float Sc, BestSc;
    local int Intel;

    Squad = SwatAIRepository(Level.AIRepo).GetElementSquad();
    PC = Level.GetLocalPlayerController();
    if (Squad == None || PC == None || PC.Pawn == None || !Squad.HasActiveMembers())
        return;
    if (Squad.IsExecutingCommandGoal() && !(bEscort && Squad.IsFallingIn()))
    {
        if (Level.TimeSeconds > NextOfficerWhy)
        {
            NextOfficerWhy = Level.TimeSeconds + 10.0;
            Cmd = "";
            if (LastOrderDoor != None)
                foreach DynamicActors(class'Pawn', P)
                    if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer'))
                        Cmd = Cmd$" "$P.Name$"="$int(VSize(P.Location - LastOrderDoor.Location))$"/v"$int(VSize(P.Velocity))$"@"$int(P.Location.X)$","$int(P.Location.Y)$","$int(P.Location.Z);
            Log("SwatMinds officers busy t="$Level.TimeSeconds$" state="$SwatRepo(Level.GetRepo()).GuiConfig.SwatGameState$" pauser="$Level.Pauser$" doordist:"$Cmd$" door@"$int(LastOrderDoor.Location.X)$","$int(LastOrderDoor.Location.Y)$" me@"$int(PC.Pawn.Location.X)$","$int(PC.Pawn.Location.Y), 'SwatMinds');
        }
        if (Level.TimeSeconds - LastOrderTime > OrderTimeout)
        {
            Log("SwatMinds officers timeout, clearing order", 'SwatMinds');
            Squad.ClearCommandGoal();
        }
        return;
    }
    Giver = PC.Pawn;

    // start gate: ordering before every officer's commander action runs asserts in Hive (crash 10-19)
    if (OfficersReadyAt <= 0.0)
    {
        foreach DynamicActors(class'Pawn', P)
            if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer') && (ISwatAI(P) == None || ISwatAI(P).GetCommanderAction() == None))
                return;
        OfficersReadyAt = Level.TimeSeconds + 3.0;  // was max(t+10, 20): officers sat in the truck too long in playtests
        if (bGhostPlayer)
        {
            Giver.SetCollision(false, false, false);
            Log("SwatMinds officers ghost player (no collision)", 'SwatMinds');
        }
        Log("SwatMinds officers ready, first order at "$OfficersReadyAt, 'SwatMinds');
    }
    if (Level.TimeSeconds < OfficersReadyAt)
        return;

    // 1. secure: compliant, not yet restrained suspects or hostages
    BestDist = 0;
    foreach DynamicActors(class'Pawn', P)
    {
        if (!(P.IsA('SwatEnemy') || P.IsA('SwatHostage')) || !P.IsConscious() || !P.IsCompliant() || ISwatAI(P).IsArrested())
            continue;
        bUsed = false;
        for (k = 0; k < SecureAsked.Length; k++)
            if (SecureAsked[k] == P)
                bUsed = true;
        if (bUsed)
            continue;
        Lead = Squad.GetClosestOfficerTo(P);
        if (Lead == None)
            continue;
        Dist = VSize(Lead.Location - P.Location);
        if (Best == None || Dist < BestDist)
            { Best = P; BestDist = Dist; }
    }
    if (Best != None)
    {
        SecureAsked[SecureAsked.Length] = Best;
        Orders++;
        LastOrderTime = Level.TimeSeconds;
        Lead = Squad.GetClosestOfficerTo(Best);
        Squad.Secure(Giver, Lead.Location, Best);
        Log("SwatMinds officers secure "$Best.Name$" dist="$int(BestDist), 'SwatMinds');
        return;
    }

    // officer intel: suspects an officer can see right now
    foreach DynamicActors(class'Pawn', P)
        if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer') && P.IsConscious())
            foreach DynamicActors(class'Pawn', Best)
                if (Best.IsA('SwatEnemy') && Best.IsConscious() && !Best.IsCompliant() && !ISwatAI(Best).IsArrested()
                    && VSize(Best.Location - P.Location) < 3000 && P.LineOfSightTo(Best))
                    AddIntel(Best.Location, "seen "$Best.Name$" by "$P.Name);
    Best = None;

    if (bEscort)
    {
        if (!Squad.IsFallingIn())
        {
            Squad.FallIn(Giver, Giver.Location);
            Orders++;
            Log("SwatMinds officers escort FallIn t="$Level.TimeSeconds, 'SwatMinds');
        }
        return;
    }

    // 2. clear: nearest door not used yet (open -> move&clear, closed -> bang&clear, locked -> breach-bang)
    BestDist = 0;
    foreach AllActors(class'Door', D)
    {
        bUsed = false;
        for (k = 0; k < UsedDoors.Length; k++)
            if (UsedDoors[k] == D)
                bUsed = true;
        if (bUsed)
            continue;
        Lead = Squad.GetClosestOfficerTo(D);
        if (Lead == None)
            continue;
        Dist = VSize(Lead.Location - D.Location);
        if (Dist > MaxDoorDist)
            continue;
        // stock squad entries need 4 stack-up points on our side (Door6 FoodWall has 0 -> script assert + stall, 10-19)
        if (SwatDoor(D) == None || SwatDoor(D).GetStackupPoints(Lead.Location).Length < 4)
            continue;
        Sc = -Dist / 1000.0;
        if (bScoreDoors)
            Sc += IntelW * IntelBehind(D, Lead.Location);
        if (BestDoor == None || Sc > BestSc)
            { BestDoor = D; BestDist = Dist; BestSc = Sc; }
    }
    if (BestDoor == None)
    {
        if (!Squad.IsFallingIn())
        {
            Squad.FallIn(Giver, Giver.Location);
            Log("SwatMinds officers FallIn t="$Level.TimeSeconds$" (no unused door within "$int(MaxDoorDist)$")", 'SwatMinds');
        }
        return;
    }
    UsedDoors[UsedDoors.Length] = BestDoor;
    LastOrderDoor = BestDoor;
    LastOrderTime = Level.TimeSeconds;
    Lead = Squad.GetClosestOfficerTo(BestDoor);
    Orders++;
    Intel = IntelBehind(BestDoor, Lead.Location);
    if (bScoreDoors)
    {
        // CQB: flash only rooms we know are occupied; quiet entry otherwise
        if (BestDoor.IsLocked())
            { if (Intel > 0) { Squad.BreachBangAndClear(Giver, Lead.Location, BestDoor); Cmd = "BreachBangAndClear"; }
              else { Squad.BreachAndClear(Giver, Lead.Location, BestDoor); Cmd = "BreachAndClear"; } }
        else if (Intel > 0)
            { Squad.BangAndClear(Giver, Lead.Location, BestDoor); Cmd = "BangAndClear"; }
        else
            { Squad.MoveAndClear(Giver, Lead.Location, BestDoor); Cmd = "MoveAndClear"; }
    }
    else if (BestDoor.IsOpen() || BestDoor.IsBroken())
        { Squad.MoveAndClear(Giver, Lead.Location, BestDoor); Cmd = "MoveAndClear"; }
    else if (BestDoor.IsLocked())
        { Squad.BreachBangAndClear(Giver, Lead.Location, BestDoor); Cmd = "BreachBangAndClear"; }
    else
        { Squad.BangAndClear(Giver, Lead.Location, BestDoor); Cmd = "BangAndClear"; }
    Log("SwatMinds officers "$Cmd$" "$BestDoor.Name$" dist="$int(BestDist)$" open="$BestDoor.IsOpen()$" locked="$BestDoor.IsLocked()$" intel="$Intel$" score="$BestSc, 'SwatMinds');
}

function ClearSectors()
{
    local int k;

    for (k = 0; k < SectorGoals.Length; k++)
        if (SectorGoals[k] != None)
        {
            SectorGoals[k].unPostGoal(None);
            SectorGoals[k].Release();
        }
    SectorGoals.Length = 0;
    SectorPawns.Length = 0;
    SectorPosted.Length = 0;
}

// escort "train" (playtest 6 wish): the player is point and covers the front; the officers behind
// are ordered by how far back they stand. The last one covers the rear, the others each cover the side
// they stand on (alternating if two stand on the same side). Lanes are parallel to the player's facing,
// measured from each officer, and are refreshed every tick, so it also holds while moving.
// AimAtPointGoal pri 40 < attack 80 / engage 85: a spotted enemy still wins.
function UpdateSectors()
{
    local OfficerTeamInfo Squad;
    local PlayerController PC;
    local Pawn Me, P;
    local array<Pawn> Offs;
    local array<float> Back;
    local vector Fwd, Rt, Eye, End, HitL, HitN, Pt;
    local int k, j, m, Off, PrevSide, Side;
    local float T;
    local AimAtPointGoal G;
    local string Sig, S;

    Squad = SwatAIRepository(Level.AIRepo).GetElementSquad();
    PC = Level.GetLocalPlayerController();
    if (Squad == None || PC == None || PC.Pawn == None || !Squad.IsFallingIn())
    {
        if (SectorGoals.Length > 0)
            ClearSectors();
        ClearCover();
        ClearBubble();
        return;
    }
    Me = PC.Pawn;
    TrainPawns.Length = 0;
    TrainYaw.Length = 0;
    Fwd = vector(MakeRot(Me.Rotation.Yaw));
    Rt = vector(MakeRot(Me.Rotation.Yaw + 16384));

    // column order: closest behind the player first
    foreach DynamicActors(class'Pawn', P)
        if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer') && P.IsConscious() && AI_Resource(P.WeaponAI) != None)
        {
            T = (Me.Location - P.Location) dot Fwd;
            k = 0;
            while (k < Back.Length && Back[k] <= T)
                k++;
            Offs.Insert(k, 1); Back.Insert(k, 1);
            Offs[k] = P; Back[k] = T;
        }
    for (k = 0; k < Offs.Length; k++)
        Sig = Sig$Offs[k].Name;
    if (Sig != SectorSig)
    {
        ClearSectors();
        SectorSig = Sig;
    }
    if (Offs.Length == 0)
        return;
    if (bBubble && bPaint && bPaintInit)
    {
        if (SectorGoals.Length > 0)
            ClearSectors();
        ClearCover();
        UpdateBubble(Me, Offs);
        return;
    }
    ClearBubble();

    PrevSide = 0;
    for (k = 0; k < Offs.Length; k++)
    {
        P = Offs[k];
        if (k == Offs.Length - 1 && Offs.Length > 1)
            Off = 32768;                                   // tail: rear
        else
        {
            if (((P.Location - Me.Location) dot Rt) >= 0) Side = 1; else Side = -1;
            if (Side == PrevSide) Side = -Side;            // two on one side: alternate
            PrevSide = Side;
            if (Side > 0) Off = 16384; else Off = 49152;
        }
        Eye = P.Location + vect(0,0,40);
        End = Eye + 1200.0 * vector(MakeRot(Me.Rotation.Yaw + Off));
        if (Trace(HitL, HitN, End, Eye, false) != None)
            Pt = HitL;
        else
            Pt = End;
        TrainPawns[k] = P;
        TrainYaw[k] = Me.Rotation.Yaw + Off;
        if (bPaint)
            Pt = DeadSpace(P, Me.Rotation.Yaw + Off, Pt);

        G = None;
        m = -1;
        for (j = 0; j < SectorPawns.Length; j++)
            if (SectorPawns[j] == P)
                { G = SectorGoals[j]; m = j; }
        if (G == None)
        {
            j = SectorGoals.Length;
            SectorPawns[j] = P;
            SectorGoals[j] = PostSector(P, Pt);
            SectorPosted[j] = Level.TimeSeconds;
            S = S$" "$P.Name$"="$(Off * 360 / 65536);
        }
        else
        {
            G.Point = Pt;
            if (AimAtPointAction(G.achievingAction) != None)
                AimAtPointAction(G.achievingAction).Point = Pt;
            else if (Level.TimeSeconds - SectorPosted[m] > 2.0)
            {
                // the action ends when the body cannot turn that far (e.g. rear while walking): re-post
                G.unPostGoal(None);
                G.Release();
                SectorGoals[m] = PostSector(P, Pt);
                SectorPosted[m] = Level.TimeSeconds;
            }
        }
    }
    if (S != "")
        Log("SwatMinds escort train t="$Level.TimeSeconds$S, 'SwatMinds');
    if (bCoverHold)
        UpdateCover(Me);
}

// ---- escort "bubble" (10-21, user: "instead of like just following like a train ... baldurs gate movement
// formation like random assortments of positionements relative to the player ... autonomy to choose when to cover
// someone, when to move and secure hostage or gun/evidence") ----
// Replaces the train when bBubble. Every ~BubbleThink s each officer picks a job. Restrain a compliant person or
// secure evidence near the player only when no threat was seen for 3 s and at least one officer stays on guard;
// the job is dropped as soon as a threat shows. Otherwise guard: a nav spot BubbleMin..BubbleMax from where the
// player will be, in sight of it, scored by cover facing out from the player (CoverScore), view on the oldest
// unpainted threat points, sight of a busy officer, the officer's own random bearing (re-rolled every 15-25 s:
// the random assortment), spacing, minus travel. It aims at the oldest unpainted threat it can see from there.
// MoveToLocationGoal 95 beats the FallIn formation (90); restrain/evidence goals are pri 80 on characterAI.
function UpdateBubble(Pawn Me, array<Pawn> Offs)
{
    local int k, b, i, j, Busy;
    local Pawn P, E;
    local Actor A, BestA;
    local NavigationPoint NP;
    local vector C, L, BestL, Aim;
    local float Sc, BestSc, Now;
    local bool bOk, bFound;
    local string S;

    Now = Level.TimeSeconds;
    C = Me.Location + 0.8 * Me.Velocity;

    // any live threat in sight of the squad?
    foreach DynamicActors(class'Pawn', E)
    {
        if (!E.IsA('SwatEnemy') || !E.IsConscious() || ISwatAI(E).IsCompliant() || ISwatAI(E).IsArrested()
            || VSize(E.Location - Me.Location) > 3000)
            continue;
        bOk = Me.LineOfSightTo(E);
        for (k = 0; k < Offs.Length && !bOk; k++)
            bOk = Offs[k].LineOfSightTo(E);
        if (bOk)
            BubThreatT = Now;
    }

    // evidence list (dropped guns are HandheldEquipmentModel), refreshed every 2 s
    if (Now > BubEvidT)
    {
        BubEvidT = Now + 2.0;
        BubEvid.Length = 0;
        foreach DynamicActors(class'Actor', A)
            if (A.IsA('IEvidence') && IEvidence(A).CanBeUsedNow())
                BubEvid[BubEvid.Length] = A;
    }

    // oldest unpainted threat navs (up to 8)
    BubOld.Length = 0;
    for (k = 0; k < ThreatIdx.Length; k++)
    {
        i = ThreatIdx[k];
        if (Now - PaintTime[i] < PaintFade)
            continue;
        j = 0;
        while (j < BubOld.Length && PaintTime[BubOld[j]] <= PaintTime[i])
            j++;
        if (j >= 8)
            continue;
        BubOld.Insert(j, 1);
        BubOld[j] = i;
        if (BubOld.Length > 8)
            BubOld.Length = 8;
    }

    // drop slots of officers that left
    for (b = BubPawn.Length - 1; b >= 0; b--)
    {
        bOk = false;
        for (k = 0; k < Offs.Length; k++)
            if (Offs[k] == BubPawn[b])
                bOk = true;
        if (!bOk)
            RemoveBubSlot(b);
    }

    // running jobs
    Busy = 0;
    for (k = 0; k < Offs.Length; k++)
    {
        b = BubSlot(Offs[k]);
        if (BubTask[b] == 0)
            continue;
        bOk = Now - BubThreatT > 2.0 && BubTarget[b] != None;
        if (bOk && BubTask[b] == 1)
            bOk = BubRR[b] != None && !BubRR[b].hasCompleted() && Pawn(BubTarget[b]).IsConscious()
                && !ISwatAI(BubTarget[b]).IsArrested();
        if (bOk && BubTask[b] == 2)
            bOk = BubSE[b] != None && !BubSE[b].hasCompleted() && IEvidence(BubTarget[b]).CanBeUsedNow();
        if (bOk)
        {
            Busy++;
            continue;
        }
        S = S$" "$Offs[k].Name$"=done";
        ReleaseBubJob(b);
        BubNext[b] = 0;
    }

    for (k = 0; k < Offs.Length; k++)
    {
        P = Offs[k];
        b = BubSlot(P);
        if (BubTask[b] != 0)
            continue;
        if (Now > BubBiasT[b])
        {
            BubBias[b] = Rand(65536);
            BubBiasT[b] = Now + 15.0 + 10.0 * FRand();
        }
        if (Now >= BubNext[b])
        {
            BubNext[b] = Now + BubbleThink * (0.75 + 0.5 * FRand());

            // a job near the player?
            if (Busy < Offs.Length - 1 && Now - BubThreatT > 3.0)
            {
                BestA = None;
                BestSc = -999;
                foreach DynamicActors(class'Pawn', E)
                    if ((E.IsA('SwatEnemy') || E.IsA('SwatHostage')) && E.IsConscious() && ISwatAI(E).IsCompliant()
                        && !ISwatAI(E).IsArrested() && VSize(E.Location - Me.Location) < SecureRange && !BubClaimed(E))
                    {
                        Sc = 2.0 - VSize(E.Location - P.Location) / 1000.0;
                        if (Sc > BestSc)
                            { BestSc = Sc; BestA = E; }
                    }
                for (i = 0; i < BubEvid.Length; i++)
                {
                    A = BubEvid[i];
                    if (A == None || !IEvidence(A).CanBeUsedNow() || VSize(A.Location - Me.Location) > SecureRange || BubClaimed(A))
                        continue;
                    Sc = 1.5 - VSize(A.Location - P.Location) / 1000.0;
                    if (Sc > BestSc)
                        { BestSc = Sc; BestA = A; }
                }
                if (BestA != None)
                {
                    ReleaseBubGuard(b);
                    BubTarget[b] = BestA;
                    if (BestA.IsA('Pawn'))
                    {
                        BubTask[b] = 1;
                        BubRR[b] = new class'RestrainAndReportGoal'(AI_Resource(P.characterAI), Pawn(BestA));
                        BubRR[b].AddRef();
                        BubRR[b].postGoal(None);
                        BubSecN++;
                        S = S$" "$P.Name$"=restrain:"$BestA.Name;
                    }
                    else
                    {
                        BubTask[b] = 2;
                        BubSE[b] = new class'SecureEvidenceGoal'(AI_Resource(P.characterAI), IEvidence(BestA));
                        BubSE[b].AddRef();
                        BubSE[b].postGoal(None);
                        BubEvN++;
                        S = S$" "$P.Name$"=evidence:"$BestA.Name;
                    }
                    Busy++;
                    continue;
                }
            }

            // guard spot (keep the current one unless clearly better)
            BestSc = -999;
            if (BubPt[b] != vect(0,0,0))
                BestSc = GuardScore(b, P, BubPt[b], C, Busy > 0) + 0.2;
            bFound = false;
            for (i = 0; i < PaintNav.Length; i++)
            {
                NP = PaintNav[i];
                if (NP == None)
                    continue;
                L = NP.Location;
                Sc = VSize(L - C);
                if (Sc < BubbleMin || Sc > BubbleMax || Abs(L.Z - Me.Location.Z) > 80
                    || !FastTrace(L + vect(0,0,40), C + vect(0,0,40)))
                    continue;
                Sc = GuardScore(b, P, L, C, Busy > 0) + 0.15 * FRand();
                if (Sc > BestSc)
                    { BestSc = Sc; BestL = L; bFound = true; }
            }
            if (bFound)
            {
                BubPt[b] = BestL;
                S = S$" "$P.Name$"=guard:"$int(VSize(BestL - C));
            }
        }
        if (BubPt[b] == vect(0,0,0))
            continue;

        // go to / hold the spot
        if (BubMove[b] == None || VSize(BubMovePt[b] - BubPt[b]) > 10
            || ((BubMove[b].hasCompleted() || BubMove[b].achievingAction == None) && Now - BubMoveT[b] > 1.0
                && VSize(P.Location - BubPt[b]) > 60))
        {
            if (BubMove[b] != None)
            {
                BubMove[b].unPostGoal(None);
                BubMove[b].Release();
            }
            BubMove[b] = PostMove(P, BubPt[b]);
            BubMovePt[b] = BubPt[b];
            BubMoveT[b] = Now;
        }

        // aim: oldest unpainted threat in sight of the spot, else straight out from the player
        bFound = false;
        for (j = 0; j < BubOld.Length && !bFound; j++)
        {
            L = PaintNav[BubOld[j]].Location;
            if (VSize(L - BubPt[b]) < PaintRange && FastTrace(L + vect(0,0,40), BubPt[b] + vect(0,0,40)))
            {
                Aim = L + vect(0,0,40);
                bFound = true;
            }
        }
        if (!bFound)
        {
            L = BubPt[b] - C;
            L.Z = 0;
            if (VSize(L) < 1)
                L = vector(MakeRot(BubBias[b]));
            Aim = BubPt[b] + vect(0,0,40) + 600.0 * Normal(L);
        }
        if (BubAim[b] == None)
        {
            BubAim[b] = PostSector(P, Aim);
            BubAimT[b] = Now;
        }
        else
        {
            BubAim[b].Point = Aim;
            if (AimAtPointAction(BubAim[b].achievingAction) != None)
                AimAtPointAction(BubAim[b].achievingAction).Point = Aim;
            else if (Now - BubAimT[b] > 2.0)
            {
                BubAim[b].unPostGoal(None);
                BubAim[b].Release();
                BubAim[b] = PostSector(P, Aim);
                BubAimT[b] = Now;
            }
        }
    }
    if (S != "")
        SideLog("SwatMinds bubble t="$int(Now)$S);
}

function float GuardScore(int b, Pawn P, vector L, vector C, bool bCoverMates)
{
    local vector Fw;
    local float Sc;
    local int j, n;

    Fw = L - C;
    Fw.Z = 0;
    if (VSize(Fw) < 1)
        Fw = vector(MakeRot(BubBias[b]));
    Fw = Normal(Fw);
    Sc = CoverScore(L, Fw);
    for (j = 0; j < BubOld.Length; j++)
        if (VSize(PaintNav[BubOld[j]].Location - L) < PaintRange
            && FastTrace(PaintNav[BubOld[j]].Location + vect(0,0,40), L + vect(0,0,40)))
            n++;
    if (BubOld.Length > 0)
        Sc += 0.8 * n / BubOld.Length;
    Sc += 0.5 * (Fw dot vector(MakeRot(BubBias[b])));
    Sc -= VSize(L - P.Location) / 1500.0;
    for (j = 0; j < BubPawn.Length; j++)
    {
        if (j == b || BubPawn[j] == None)
            continue;
        if (BubTask[j] == 0 && BubPt[j] != vect(0,0,0) && VSize(BubPt[j] - L) < 160)
            Sc -= 1.0;
        if (bCoverMates && BubTask[j] != 0 && FastTrace(BubPawn[j].Location + vect(0,0,40), L + vect(0,0,40)))
            Sc += 0.4;     // cover a teammate who is restraining / bagging evidence
    }
    return Sc;
}

function int BubSlot(Pawn P)
{
    local int b;

    for (b = 0; b < BubPawn.Length; b++)
        if (BubPawn[b] == P)
            return b;
    b = BubPawn.Length;
    BubPawn[b] = P; BubTask[b] = 0; BubTarget[b] = None; BubPt[b] = vect(0,0,0); BubMovePt[b] = vect(0,0,0);
    BubNext[b] = 0; BubBiasT[b] = 0; BubAimT[b] = 0; BubMoveT[b] = 0; BubBias[b] = 0;
    BubMove[b] = None; BubAim[b] = None; BubRR[b] = None; BubSE[b] = None;
    return b;
}

function bool BubClaimed(Actor A)
{
    local int b;

    for (b = 0; b < BubPawn.Length; b++)
        if (BubTask[b] != 0 && BubTarget[b] == A)
            return true;
    return false;
}

function ReleaseBubGuard(int b)
{
    if (BubMove[b] != None)
    {
        BubMove[b].unPostGoal(None);
        BubMove[b].Release();
        BubMove[b] = None;
    }
    if (BubAim[b] != None)
    {
        BubAim[b].unPostGoal(None);
        BubAim[b].Release();
        BubAim[b] = None;
    }
    BubPt[b] = vect(0,0,0);
}

function ReleaseBubJob(int b)
{
    if (BubRR[b] != None)
    {
        BubRR[b].unPostGoal(None);
        BubRR[b].Release();
        BubRR[b] = None;
    }
    if (BubSE[b] != None)
    {
        BubSE[b].unPostGoal(None);
        BubSE[b].Release();
        BubSE[b] = None;
    }
    BubTask[b] = 0;
    BubTarget[b] = None;
}

function RemoveBubSlot(int b)
{
    ReleaseBubGuard(b);
    ReleaseBubJob(b);
    BubPawn.Remove(b, 1); BubTask.Remove(b, 1); BubTarget.Remove(b, 1); BubPt.Remove(b, 1); BubMovePt.Remove(b, 1);
    BubNext.Remove(b, 1); BubBiasT.Remove(b, 1); BubAimT.Remove(b, 1); BubMoveT.Remove(b, 1); BubBias.Remove(b, 1);
    BubMove.Remove(b, 1); BubAim.Remove(b, 1); BubRR.Remove(b, 1); BubSE.Remove(b, 1);
}

function ClearBubble()
{
    while (BubPawn.Length > 0)
        RemoveBubSlot(BubPawn.Length - 1);
}

// ---- coverage paint (10-20, user idea: "they 'paint' the walls to guarantee no hidden places") ----
// Threat points = nav points within PaintRange that some squad eye can see. A point is painted when a
// squad member aims within the cone at it with LOS; paint fades after PaintFade s. Share = painted/threats.
function UpdatePaint()
{
    local NavigationPoint NP;
    local PlayerController PC;
    local Pawn P, Me;
    local vector L, D, F;
    local int i, k, n, Painted;
    local bool bLOS;

    if (!bPaintInit)
    {
        foreach AllActors(class'NavigationPoint', NP)
            PaintNav[PaintNav.Length] = NP;
        PaintTime.Length = PaintNav.Length;
        PaintThreat.Length = PaintNav.Length;
        bPaintInit = true;
        Log("SwatMinds paint navs="$PaintNav.Length, 'SwatMinds');
    }
    SqEye.Length = 0;
    SqDir.Length = 0;
    SqC = vect(0,0,0);
    PC = Level.GetLocalPlayerController();
    if (PC != None && PC.Pawn != None && !bGhostPlayer && PC.Pawn.IsConscious())
    {
        Me = PC.Pawn;
        SqEye[0] = Me.Location + Me.EyePosition();
        F = vector(Me.GetViewRotation()); F.Z = 0;
        SqDir[0] = Normal(F);
    }
    foreach DynamicActors(class'Pawn', P)
        if (P.IsA('SwatOfficer') && !P.IsA('SwatPlayer') && P.IsConscious() && ISwatAI(P) != None)
        {
            k = SqEye.Length;
            SqEye[k] = P.Location + P.EyePosition();
            F = vector(ISwatAI(P).GetAimOrientation()); F.Z = 0;
            SqDir[k] = Normal(F);
            SqC += P.Location;
            n++;
        }
    if (SqEye.Length == 0)
        return;
    if (Me != None && (bEscort || n == 0))
        SqC = Me.Location;
    else
        SqC = SqC / n;

    ThreatIdx.Length = 0;
    for (i = 0; i < PaintNav.Length; i++)
    {
        PaintThreat[i] = 0;
        if (PaintNav[i] == None)
            continue;
        L = PaintNav[i].Location + vect(0,0,40);
        if (VSize(L - SqC) > PaintRange || Abs(L.Z - SqC.Z) > 300)
            continue;
        bLOS = false;
        for (k = 0; k < SqEye.Length; k++)
            if (FastTrace(L, SqEye[k]))
            {
                bLOS = true;
                D = L - SqEye[k]; D.Z = 0;
                if (VSize(D) < 80 || (Normal(D) dot SqDir[k]) > PaintCone)
                {
                    PaintTime[i] = Level.TimeSeconds;
                    break;
                }
            }
        if (!bLOS)
            continue;
        PaintThreat[i] = 1;
        ThreatIdx[ThreatIdx.Length] = i;
        if (Level.TimeSeconds - PaintTime[i] <= PaintFade)
            Painted++;
    }
    if (ThreatIdx.Length > 0)
    {
        PaintShare = float(Painted) / ThreatIdx.Length;
        PaintSum += PaintShare;
        PaintN++;
    }
    if (Level.TimeSeconds >= NextPaintLog)
    {
        NextPaintLog = Level.TimeSeconds + 5.0;
        Log("SwatMinds paint t="$int(Level.TimeSeconds)$" share="$PaintShare$" threats="$ThreatIdx.Length$" painted="$Painted$" squad="$SqEye.Length, 'SwatMinds');
    }
}

// dead space: instead of the plain lane, look at the oldest unpainted threat point within 90 deg of the
// officer's train sector (the sector is the prior). Held DeadHold s or until painted; one officer per point.
function vector DeadSpace(Pawn P, int Yaw, vector Lane)
{
    local int i, j, q, Me, Best;
    local float Age, BestAge;
    local vector Eye, D, Fw;
    local bool bTaken;

    if (!bPaintInit)
        return Lane;
    Me = -1;
    for (j = 0; j < DeadPawns.Length; j++)
        if (DeadPawns[j] == P)
            Me = j;
    if (Me < 0)
    {
        Me = DeadPawns.Length;
        DeadPawns[Me] = P;
        DeadIdx[Me] = -1;
        DeadUntil[Me] = 0;
    }
    if (DeadIdx[Me] >= 0 && Level.TimeSeconds < DeadUntil[Me] && Level.TimeSeconds - PaintTime[DeadIdx[Me]] > PaintFade)
        return PaintNav[DeadIdx[Me]].Location + vect(0,0,40);
    DeadIdx[Me] = -1;
    Eye = P.Location + P.EyePosition();
    Fw = vector(MakeRot(Yaw));
    Best = -1;
    BestAge = PaintFade;
    for (q = 0; q < ThreatIdx.Length; q++)
    {
        i = ThreatIdx[q];
        Age = Level.TimeSeconds - PaintTime[i];
        if (Age <= BestAge)
            continue;
        D = PaintNav[i].Location - P.Location; D.Z = 0;
        if (VSize(D) < 150 || (Normal(D) dot Fw) < 0.0)
            continue;
        bTaken = false;
        for (j = 0; j < DeadPawns.Length; j++)
            if (j != Me && DeadIdx[j] == i && Level.TimeSeconds < DeadUntil[j])
                bTaken = true;
        if (bTaken || !FastTrace(PaintNav[i].Location + vect(0,0,40), Eye))
            continue;
        Best = i;
        BestAge = Age;
    }
    if (Best < 0)
        return Lane;
    DeadIdx[Me] = Best;
    DeadUntil[Me] = Level.TimeSeconds + DeadHold;
    return PaintNav[Best].Location + vect(0,0,40);
}

// ---- halt: cover spots + shoulder tap (10-20) ----
// Player still for HaltTime: each officer moves to a nearby nav spot that sees down its sector with a wall
// at its back / an edge beside it (MoveToLocationGoal 95 beats MoveInFormationGoal 90; re-posted if it ends).
// Tap = all sector aims set; logged as time from halt. When the player moves on, cover is dropped, but the
// tail keeps holding the rear until the gap to the next officer passes TapGap (then it "taps out").
function UpdateCover(Pawn Me)
{
    local int k, j, i;
    local Pawn P, Tail;
    local vector Fw, L, Best;
    local float Sc, BestSc;
    local bool bAll, bFound, bNear;
    local AimAtPointGoal G;
    local string S;

    if (TrainPawns.Length > 0)
        Tail = TrainPawns[TrainPawns.Length - 1];
    if (VSize(Me.Location - HaltLoc) > 120)
    {
        HaltLoc = Me.Location;
        HaltSince = Level.TimeSeconds;
        bTapDone = false;
        bCoverDone = false;
    }
    if (Level.TimeSeconds - HaltSince < HaltTime)
    {
        k = CoverPawns.Length - 1;
        while (k >= 0)
        {
            P = CoverPawns[k];
            if (TrainPawns.Length > 1 && P == Tail
                && VSize(P.Location - TrainPawns[TrainPawns.Length - 2].Location) < TapGap
                && Level.TimeSeconds - CoverPosted[k] < 8.0)
            {
                k--;
                continue;
            }
            if (P == Tail)
                Log("SwatMinds tail tap-out t="$int(Level.TimeSeconds)$" "$P.Name, 'SwatMinds');
            ReleaseCover(k);
            k--;
        }
        return;
    }

    // halted: shoulder tap = every sector aim is set
    if (!bTapDone && TrainPawns.Length > 0)
    {
        bAll = true;
        for (k = 0; k < TrainPawns.Length; k++)
        {
            G = None;
            for (j = 0; j < SectorPawns.Length; j++)
                if (SectorPawns[j] == TrainPawns[k])
                    G = SectorGoals[j];
            if (G == None || G.achievingAction == None)
                bAll = false;
            else
            {
                Fw = G.Point - TrainPawns[k].Location; Fw.Z = 0;
                L = vector(ISwatAI(TrainPawns[k]).GetAimOrientation()); L.Z = 0;
                if ((Normal(Fw) dot Normal(L)) < 0.9)
                    bAll = false;
            }
        }
        if (bAll)
        {
            bTapDone = true;
            TapSum += Level.TimeSeconds - HaltSince;
            TapN++;
            Log("SwatMinds tap t="$int(Level.TimeSeconds)$" dt="$(Level.TimeSeconds - HaltSince)$" n="$TrainPawns.Length, 'SwatMinds');
        }
    }

    // keep holds alive
    for (k = 0; k < CoverGoals.Length; k++)
        if (CoverGoals[k].achievingAction == None && Level.TimeSeconds - CoverPosted[k] > 1.0
            && VSize(CoverPawns[k].Location - CoverPts[k]) > 60)
        {
            CoverGoals[k].unPostGoal(None);
            CoverGoals[k].Release();
            CoverGoals[k] = PostMove(CoverPawns[k], CoverPts[k]);
            CoverPosted[k] = Level.TimeSeconds;
        }
    if (bCoverDone || !bPaintInit)
        return;
    bCoverDone = true;
    for (k = 0; k < TrainPawns.Length; k++)
    {
        P = TrainPawns[k];
        bNear = false;
        for (j = 0; j < CoverPawns.Length; j++)
            if (CoverPawns[j] == P)
                bNear = true;
        if (bNear)
            continue;      // tail still holding from the last halt
        Fw = vector(MakeRot(TrainYaw[k]));
        BestSc = CoverScore(P.Location, Fw) + 0.2;   // moving must be clearly better
        bFound = false;
        for (i = 0; i < PaintNav.Length; i++)
        {
            if (PaintNav[i] == None)
                continue;
            L = PaintNav[i].Location;
            if (VSize(L - P.Location) > CoverSearch || VSize(L - Me.Location) > 700 || Abs(L.Z - P.Location.Z) > 80)
                continue;
            bNear = false;
            for (j = 0; j < CoverPts.Length; j++)
                if (VSize(L - CoverPts[j]) < 80)
                    bNear = true;
            if (bNear || VSize(L - Me.Location) < 80 || !FastTrace(L + vect(0,0,40), P.Location + vect(0,0,40)))
                continue;
            Sc = CoverScore(L, Fw) - VSize(L - P.Location) / 1000.0;
            if (Sc > BestSc)
            {
                BestSc = Sc;
                Best = L;
                bFound = true;
            }
        }
        if (bFound)
        {
            j = CoverGoals.Length;
            CoverPawns[j] = P;
            CoverPts[j] = Best;
            CoverGoals[j] = PostMove(P, Best);
            CoverPosted[j] = Level.TimeSeconds;
            S = S$" "$P.Name$"="$int(VSize(Best - P.Location))$"/"$BestSc;
        }
    }
    if (S != "")
        Log("SwatMinds cover t="$int(Level.TimeSeconds)$S, 'SwatMinds');
}

// sector view length (0..1) + wall at the back + edge (wall on exactly one side)
function float CoverScore(vector L, vector Fw)
{
    local vector E, Rt, HitL, HitN;
    local float Sc;
    local bool A, B;

    E = L + vect(0,0,40);
    Rt = Fw cross vect(0,0,1);
    if (Trace(HitL, HitN, E + 1200.0 * Fw, E, false) != None)
        Sc = VSize(HitL - E) / 1200.0;
    else
        Sc = 1.0;
    if (!FastTrace(E - 150.0 * Fw, E))
        Sc += 0.4;
    A = !FastTrace(E + 120.0 * Rt, E);
    B = !FastTrace(E - 120.0 * Rt, E);
    if (A != B)
        Sc += 0.3;
    return Sc;
}

function MoveToLocationGoal PostMove(Pawn P, vector L)
{
    local MoveToLocationGoal G;

    G = new class'MoveToLocationGoal'(AI_Resource(P.MovementAI), 95, L);
    G.SetAcceptNearbyPath(true);
    G.AddRef();
    G.postGoal(None);
    return G;
}

function ReleaseCover(int k)
{
    if (CoverGoals[k] != None)
    {
        CoverGoals[k].unPostGoal(None);
        CoverGoals[k].Release();
    }
    CoverGoals.Remove(k, 1);
    CoverPawns.Remove(k, 1);
    CoverPts.Remove(k, 1);
    CoverPosted.Remove(k, 1);
}

function ClearCover()
{
    while (CoverGoals.Length > 0)
        ReleaseCover(CoverGoals.Length - 1);
}

// ---- director (10-20, user: "we will add the director ai into the game too") ----
// Every ~DirectorInterval s: the out-of-sight nav point (DirectorMin..DirectorRange from the squad) that was
// painted longest ago. The nearest free suspect that the squad cannot see is sent there; with no suspect the
// point is a virtual probe. Time-to-face = first squad LOS on the threat -> a squad aim cone on it.
function int SusRounds(Pawn E)
{
    local HandheldEquipment W;
    W = E.GetActiveItem();
    if (W == None || !W.IsA('FiredWeapon') || FiredWeapon(W).Ammo == None)
        return -1;
    return FiredWeapon(W).Ammo.RoundsRemainingBeforeReload();
}

function bool HoldOn(int i)
{
    local Pawn E;
    E = CwPawn[i];
    return E != None && E.IsConscious() && !ISwatAI(E).IsCompliant() && !ISwatAI(E).IsArrested()
        && CwSince[i] > 0 && CwFired[i] == 0 && Level.TimeSeconds - CwSince[i] < ComplyWait;
}

function UpdateComply()
{
    local Pawn E, O;
    local int i, k, R;
    local bool bHas;
    local OrderComplianceGoal G;

    foreach DynamicActors(class'Pawn', E)
    {
        if (!E.IsA('SwatEnemy'))
            continue;
        for (i = 0; i < CwPawn.Length; i++)
            if (CwPawn[i] == E)
                break;
        if (i == CwPawn.Length)
        {
            CwPawn[i] = E; CwRounds[i] = SusRounds(E); CwSince[i] = 0; CwFired[i] = 0; CwHeld[i] = 0; CwDone[i] = 0;
        }
        if (CwHeld[i] == 1 && CwDone[i] == 0 && E.IsConscious() && (ISwatAI(E).IsCompliant() || ISwatAI(E).IsArrested()))
        {
            CwDone[i] = 1;
            CwComply++;
            SideLog("SwatMinds comply t="$int(Level.TimeSeconds)$" "$E.Name$" complied during/after hold");
        }
        if (!E.IsConscious() || ISwatAI(E).IsCompliant() || ISwatAI(E).IsArrested())
            continue;
        R = SusRounds(E);
        if (R >= 0 && CwRounds[i] >= 0 && R < CwRounds[i] && CwSince[i] > 0 && CwFired[i] == 0)
        {
            CwFired[i] = 1;
            if (Level.TimeSeconds - CwSince[i] < ComplyWait)
            {
                CwShot++;
                SideLog("SwatMinds comply t="$int(Level.TimeSeconds)$" "$E.Name$" fired, hold off");
            }
        }
        CwRounds[i] = R;
        if (CwSince[i] == 0 && ISwatEnemy(E).IsAThreat())
            CwSince[i] = Level.TimeSeconds;
    }

    // drop holds that are over or whose goal finished (re-posted below while the hold lasts)
    for (k = HoldG.Length - 1; k >= 0; k--)
    {
        for (i = 0; i < CwPawn.Length; i++)
            if (CwPawn[i] == HoldE[k])
                break;
        if (i < CwPawn.Length && HoldOn(i) && HoldO[k] != None && HoldO[k].IsConscious() && !HoldG[k].hasCompleted())
            continue;
        HoldG[k].unPostGoal(None);
        HoldG[k].Release();
        HoldG.Remove(k, 1); HoldO.Remove(k, 1); HoldE.Remove(k, 1);
    }

    for (i = 0; i < CwPawn.Length; i++)
    {
        if (!HoldOn(i))
            continue;
        E = CwPawn[i];
        foreach DynamicActors(class'Pawn', O)
        {
            if (!O.IsA('SwatOfficer') || O.IsA('SwatPlayer') || !O.IsConscious() || O.WeaponAI == None)
                continue;
            if (VSize(O.Location - E.Location) > 2500.0 || !O.LineOfSightTo(E))
                continue;
            bHas = false;
            for (k = 0; k < HoldO.Length; k++)
                if (HoldO[k] == O)
                    bHas = true;
            if (bHas)
                continue;
            G = new class'OrderComplianceGoal'(AI_Resource(O.WeaponAI), E);
            G.AddRef();
            G.postGoal(None);
            HoldG[HoldG.Length] = G; HoldO[HoldO.Length] = O; HoldE[HoldE.Length] = E;
            CwHold++;
            if (CwHeld[i] == 0)
                SideLog("SwatMinds comply t="$int(Level.TimeSeconds)$" "$O.Name$" holds fire on "$E.Name$", shouting");
            CwHeld[i] = 1;
        }
    }
}

function UpdateDirector()
{
    local int i, k, Best;
    local float Sc, BestSc, D, BestD;
    local vector L, T, V;
    local Pawn E, BestE;
    local bool bSeen, bFaced;

    if (DirStart > 0)
    {
        if (DirPawn != None && (DirPawn.bDeleteMe || !DirPawn.IsConscious() || ISwatAI(DirPawn).IsArrested()))
        {
            Log("SwatMinds director end (down/arrested) t="$int(Level.TimeSeconds), 'SwatMinds');
            EndDirector();
            return;
        }
        if (DirPawn != None)
            T = DirPawn.Location + vect(0,0,40);
        else
            T = DirPt;
        for (k = 0; k < SqEye.Length; k++)
            if (FastTrace(T, SqEye[k]))
            {
                bSeen = true;
                V = T - SqEye[k]; V.Z = 0;
                if ((Normal(V) dot SqDir[k]) > PaintCone)
                    bFaced = true;
            }
        if (bSeen && DirSeenAt == 0)
            DirSeenAt = Level.TimeSeconds;
        if (bFaced)
        {
            DirFaceSum += Level.TimeSeconds - DirSeenAt;
            DirN++;
            Log("SwatMinds director faced t="$int(Level.TimeSeconds)$" face="$(Level.TimeSeconds - DirSeenAt)$" by="$DirPawn, 'SwatMinds');
            EndDirector();
        }
        else if (Level.TimeSeconds - DirStart > DirectorTimeout)
        {
            if (DirSeenAt > 0)
                DirMiss++;
            else
                DirNoShow++;
            if (DirPawn != None)
                D = VSize(DirPawn.Location - DirPt);
            Log("SwatMinds director timeout t="$int(Level.TimeSeconds)$" seen="$(DirSeenAt > 0)$" by="$DirPawn$" left="$int(D)$" act="$(DirGoal != None && DirGoal.achievingAction != None), 'SwatMinds');
            EndDirector();
        }
        return;
    }
    if (NextDirector == 0)
        NextDirector = Level.TimeSeconds + 0.5 * DirectorInterval;
    if (Level.TimeSeconds < NextDirector || SqEye.Length == 0)
        return;
    NextDirector = Level.TimeSeconds + DirectorInterval * (0.75 + 0.5 * FRand());

    Best = -1;
    BestSc = -1;
    for (i = 0; i < PaintNav.Length; i++)
    {
        if (PaintNav[i] == None || PaintThreat[i] != 1)
            continue;
        L = PaintNav[i].Location + vect(0,0,40);
        D = VSize(L - SqC);
        if (D < DirectorMin || D > DirectorRange || Abs(L.Z - SqC.Z) > 400)
            continue;
        Sc = Level.TimeSeconds - PaintTime[i] + 5.0 * FRand();
        if (Sc <= BestSc)
            continue;
        Best = i;
        BestSc = Sc;
    }
    if (Best < 0)
        return;
    DirPt = PaintNav[Best].Location + vect(0,0,40);

    BestD = DirectorRange * 1.5;
    foreach DynamicActors(class'Pawn', E)
        if (E.IsA('SwatEnemy') && E.IsConscious() && ISwatAI(E) != None && !ISwatAI(E).IsArrested() && AI_Resource(E.MovementAI) != None)
        {
            D = VSize(E.Location - DirPt);
            if (D >= BestD)
                continue;
            bSeen = false;
            for (k = 0; k < SqEye.Length; k++)
                if (FastTrace(E.Location + vect(0,0,40), SqEye[k]))
                    bSeen = true;
            if (bSeen)
                continue;
            BestE = E;
            BestD = D;
        }
    DirPawn = BestE;
    if (BestE != None)
        DirGoal = PostMove(BestE, PaintNav[Best].Location);
    DirStart = Level.TimeSeconds;
    DirSeenAt = 0;
    Log("SwatMinds director send t="$int(Level.TimeSeconds)$" pt="$int(DirPt.X)$","$int(DirPt.Y)$" age="$int(Level.TimeSeconds - PaintTime[Best])$" by="$BestE$" dist="$int(BestD), 'SwatMinds');
}

function EndDirector()
{
    if (DirGoal != None)
    {
        DirGoal.unPostGoal(None);
        DirGoal.Release();
        DirGoal = None;
    }
    DirPawn = None;
    DirStart = 0;
}

function AimAtPointGoal PostSector(Pawn P, vector Pt)
{
    local AimAtPointGoal G;

    G = new class'AimAtPointGoal'(AI_Resource(P.WeaponAI), 40, Pt);
    G.AddRef();
    G.postGoal(None);
    return G;
}

function rotator MakeRot(int Yaw)
{
    local rotator R;
    R.Yaw = Yaw;
    return R;
}

function ReapplyInstantAction()
{
    local SwatRepo Repo;
    local SwatGUIConfig Cfg;

    Repo = SwatRepo(Level.GetRepo());
    if (IAPick == "" || Repo == None || Repo.GuiConfig == None)
        return;
    Cfg = Repo.GuiConfig;
    if (Cfg.GetPropertyText("LastMissionPlayedName") == IAPick)
        return;
    Cfg.SetPropertyText("LastMissionPlayedName", IAPick);
    Cfg.SetPropertyText("LastMissionPlayedFriendlyName", IAPickFriendly);
    Cfg.SetPropertyText("LastMissionPlayedCustomScenario", "None");
    Cfg.SaveConfig();
    Log("SwatMinds instant action re-set to "$IAPick$" (GUI had overwritten it)", 'SwatMinds');
}

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
    IAPick = string(Cfg.MissionName[k]);
    IAPickFriendly = Cfg.FriendlyName[k];
    Cfg.SetPropertyText("LastMissionPlayedName", IAPick);
    Cfg.SetPropertyText("LastMissionPlayedFriendlyName", IAPickFriendly);
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
    bAlwaysTick=true
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
    LiveFile="SwatMindsLive.txt"
    LiveInterval=3.0
    bAutoOfficers=true
    bEscort=true
    bBubble=true
    BubbleThink=1.0
    BubbleMin=128
    BubbleMax=550
    SecureRange=1200
    bPaint=true
    PaintRange=1500.0
    PaintFade=3.0
    PaintCone=0.866
    DeadHold=1.5
    bCoverHold=true
    CoverSearch=400.0
    TapGap=300.0
    HaltTime=1.5
    bDirector=true
    DirectorInterval=60.0
    DirectorRange=2500.0
    DirectorMin=700.0
    DirectorTimeout=30.0
    OfficerThink=2.0
    MaxDoorDist=2500.0
    OrderTimeout=90.0
    ComplyWait=4.0
    IntelW=1.5
    IntelRange=1200.0
    IntelLife=60.0
    TrajInterval=1.0
    SpeedTarget=1.0
    MaxDilation=8.0
    bComms=true
    SayCooldown=6.0
    SayGap=2.0
    RuleCooldown=20.0
}
