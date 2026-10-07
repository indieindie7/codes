//=============================================================================
// AutoAudit - "autoplay audit": what a level's path network and wiring say
// about it, without playing (U2Pilot's triage.py collects the lines).
//
//   AUDIT NOREACH <node> <x y z>     no path leads there from where the player stands
//   AUDIT ONEWAY  <node> <x y z>     reachable, but no path leads back (a trap / softlock candidate)
//   AUDIT ITEM    <pickup> <x y z> <why>   a pickup with no navigation point near it, or near an
//                                        unreachable one
//   AUDIT TRIGGER <trigger> <x y z> <why>  the same for triggers
//   AUDIT ORPHANEVENT <actor> <event>      fires an Event no actor carries as its Tag
//   AUDIT SUMMARY nodes N links L reachable R ...
//
// Reachability is a breadth-first search over each NavigationPoint's PathList
// (its reach specs, the AI's own links), from the node nearest the player that
// has links; "back" is the same search over the links reversed. It is the
// network as built: doors and lifts that open later count as closed, so a
// level split by them shows its later parts as NOREACH.
//
// The work is spread over frames (a few hundred thousand script steps each at
// most): UnrealScript stops a call that runs over a million iterations with a
// "runaway loop" crash, which the first version hit on big levels.
//=============================================================================
class AutoAudit extends Info;

var PlayerController PC;
var array<NavigationPoint> Nodes;
var array<int> AdjFirst, AdjCount, Adj;      // forward links as node indices
var array<int> RFirst, RCount, RAdj;         // the same, reversed
var array<int> Fwd, Back;
var array<Actor> Things;                     // pickups and triggers to check
var array<name> Tags;
var array<Actor> Firers;
var int Phase, Cursor, Start, Links;
var int Reach, OneWay, Items, Trig, Orphans;

function Say(coerce string S)
{
	Log("AutoPlay: AUDIT "$S);
}

function string At(Actor A)
{
	return int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z);
}

function int IndexOf(NavigationPoint N)
{
	local int i;

	for (i = 0; i < Nodes.Length; i++)
		if (Nodes[i] == N)
			return i;
	return -1;
}

function int NearestIndex(vector P, out float D, bool bLinked)
{
	local int i, Best;
	local float d1;

	D = 1000000000.0;
	Best = -1;
	for (i = 0; i < Nodes.Length; i++)
	{
		if (bLinked && Nodes[i].PathList.Length == 0)
			continue;
		d1 = VSize(Nodes[i].Location - P);
		if (d1 < D)
		{
			D = d1;
			Best = i;
		}
	}
	return Best;
}

function Run(PlayerController P)
{
	local NavigationPoint N;
	local Actor A;

	PC = P;
	if (PC == None || PC.Pawn == None)
	{
		Say("SUMMARY no player");
		Destroy();
		return;
	}
	for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		Nodes[Nodes.Length] = N;
		Links += N.PathList.Length;
	}
	foreach AllActors(class'Actor', A)
	{
		if (A.IsA('Pickup') || A.IsA('Triggers'))
			Things[Things.Length] = A;
		if (A.Tag != '' && A.Tag != A.Class.Name)
			Tags[Tags.Length] = A.Tag;
		if (A.Event != '' && A.Event != 'None')
			Firers[Firers.Length] = A;
	}
	if (Nodes.Length == 0)
	{
		Say("SUMMARY no navigation points");
		Destroy();
		return;
	}
	Phase = 1;
	Cursor = 0;
	Say("started: "$Nodes.Length$" nodes, "$Links$" links, "$Things.Length$" pickups/triggers, "$Firers.Length$" event senders");
}

// breadth first over a flattened adjacency
function Search(int From, out array<int> First, out array<int> Count, out array<int> List, out array<int> Seen)
{
	local array<int> Queue;
	local int Head, i, k, e;

	Seen.Length = Nodes.Length;
	for (i = 0; i < Seen.Length; i++)
		Seen[i] = 0;
	Seen[From] = 1;
	Queue[0] = From;
	while (Head < Queue.Length)
	{
		i = Queue[Head++];
		for (k = 0; k < Count[i]; k++)
		{
			e = List[First[i] + k];
			if (Seen[e] == 0)
			{
				Seen[e] = 1;
				Queue[Queue.Length] = e;
			}
		}
	}
}

event Tick(float DeltaTime)
{
	local int i, k, e, cnt, Budget;
	local float D;
	local NavigationPoint N;
	local Actor A;
	local bool bTagged;

	switch (Phase)
	{
	case 1:     // forward links as indices, a slice of nodes per frame
		Budget = 0;
		while (Cursor < Nodes.Length && Budget < 150000)
		{
			N = Nodes[Cursor];
			AdjFirst[Cursor] = Adj.Length;
			cnt = 0;
			for (k = 0; k < N.PathList.Length; k++)
			{
				if (N.PathList[k] == None || N.PathList[k].bPruned)
					continue;
				e = IndexOf(N.PathList[k].End);
				Budget += Nodes.Length;
				if (e >= 0)
				{
					Adj[Adj.Length] = e;
					cnt++;
				}
			}
			AdjCount[Cursor] = cnt;
			Cursor++;
		}
		if (Cursor >= Nodes.Length)
			Phase = 2;
		return;
	case 2:     // reversed links (counting sort), then both searches
		RCount.Length = Nodes.Length;
		RFirst.Length = Nodes.Length;
		for (i = 0; i < Nodes.Length; i++)
			RCount[i] = 0;
		for (i = 0; i < Adj.Length; i++)
			RCount[Adj[i]]++;
		cnt = 0;
		for (i = 0; i < Nodes.Length; i++)
		{
			RFirst[i] = cnt;
			cnt += RCount[i];
			RCount[i] = 0;
		}
		RAdj.Length = Adj.Length;
		for (i = 0; i < Nodes.Length; i++)
			for (k = 0; k < AdjCount[i]; k++)
			{
				e = Adj[AdjFirst[i] + k];
				RAdj[RFirst[e] + RCount[e]] = i;
				RCount[e]++;
			}
		Start = NearestIndex(PC.Pawn.Location, D, true);
		if (Start < 0)
			Start = NearestIndex(PC.Pawn.Location, D, false);
		Search(Start, AdjFirst, AdjCount, Adj, Fwd);
		Search(Start, RFirst, RCount, RAdj, Back);
		for (i = 0; i < Nodes.Length; i++)
		{
			if (Fwd[i] == 0)
			{
				if (!Nodes[i].IsA('PlayerStart'))       // a start needs no way in
					Say("NOREACH "$Nodes[i].Name$" "$At(Nodes[i]));
			}
			else
			{
				Reach++;
				if (Back[i] == 0)
				{
					OneWay++;
					Say("ONEWAY "$Nodes[i].Name$" "$At(Nodes[i]));
				}
			}
		}
		Phase = 3;
		Cursor = 0;
		return;
	case 3:     // pickups and triggers: a reachable navigation point near each?
		Budget = 0;
		while (Cursor < Things.Length && Budget < 150000)
		{
			A = Things[Cursor++];
			Budget += Nodes.Length;
			if (A == None)
				continue;
			i = NearestIndex(A.Location, D, false);
			if (i < 0)
				continue;
			if (D > 800)
			{
				if (A.IsA('Pickup')) { Items++; Say("ITEM "$A.Name$" "$At(A)$" no-nav-within-16m"); }
				else { Trig++; Say("TRIGGER "$A.Name$" "$At(A)$" no-nav-within-16m"); }
			}
			else if (Fwd[i] == 0)
			{
				if (A.IsA('Pickup')) { Items++; Say("ITEM "$A.Name$" "$At(A)$" near-unreachable-"$Nodes[i].Name); }
				else { Trig++; Say("TRIGGER "$A.Name$" "$At(A)$" near-unreachable-"$Nodes[i].Name); }
			}
		}
		if (Cursor >= Things.Length)
		{
			Phase = 4;
			Cursor = 0;
		}
		return;
	case 4:     // events nobody carries as a Tag
		Budget = 0;
		while (Cursor < Firers.Length && Budget < 150000)
		{
			A = Firers[Cursor++];
			Budget += Tags.Length;
			if (A == None)
				continue;
			bTagged = false;
			for (i = 0; i < Tags.Length; i++)
				if (Tags[i] == A.Event)
				{
					bTagged = true;
					break;
				}
			if (!bTagged)
			{
				Orphans++;
				Say("ORPHANEVENT "$A.Name$" "$A.Event);
			}
		}
		if (Cursor >= Firers.Length)
			Phase = 5;
		return;
	case 5:
		Say("SUMMARY nodes "$Nodes.Length$" links "$Links$" reachable "$Reach$" oneway "$OneWay$" items "$Items$" triggers "$Trig$" orphan-events "$Orphans$" from "$Nodes[Start].Name$" (doors/lifts closed)");
		if (PC != None)
			PC.ClientMessage("[autoplay] audit: "$Reach$"/"$Nodes.Length$" nodes reachable, "$OneWay$" one-way, "$Items$" items, "$Trig$" triggers, "$Orphans$" orphan events (see the log)");
		Destroy();
		return;
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
