r"""Sanctuary Open: the site plan as data (the user, 2026-10-08: "use those [8 images] as key for the redesign; the
goal is the whole of Sanctuary in a single map, with more vehicle movement and open terrain").

One source of truth for the map generator (built on U2Prairie's make_prairie.py: static-mesh terrain tiles in a
-30720..30720 room, the Sanctuary skybox, the Manta), the creative team's review, and the drawing:

    py plan.py [out.png]      -> the site plan (places, roads, beats, the key image of each place)

REAL PLACE (the user, 2026-10-08: "use some real life world locations as geographical references"): the land is
Serra dos Carajas, Para, Brazil - the N4 iron mine on its plateau in the Amazon (Copernicus GLO-30, window
6.025-6.095 S, 50.225-50.155 W, fetched by fetch_dem.py): the LZ in the forest lowland (SW), the haul road up the
escarpment, the plant at the plateau's edge, the field on the open plateau, the power plant on the NW tableland,
the mine pit where the real N4 pit is. 6.6 km of the real place on the 61 440 UU map (~9.3 UU per real metre).

Units: Unreal units, ~50 per metre. The Manta cruises 1000-1200 UU/s (20-24 m/s), so 10 000 UU ~ 9 s of driving.
"""
import math, os, sys

WORLD = 30720
KEYS = r"C:\Users\john\Documents\design-refs\sanctuary_concepts"

# the places, in story order. x, y = centre; r = footprint radius; key = the concept image it must look like
PLACES = [
    {"id": "lz", "name": "Landing zone", "x": -14000, "y": 19000, "r": 2200, "z": 0, "key": "k_arrival.png",
     "what": "the dropship sets down in a jungle clearing at dusk; the Manta waits; the plant's stack seen over the trees (the weenie)"},
    {"id": "road_w", "name": "Jungle haul road", "x": -7000, "y": 9000, "r": 0, "z": 0, "key": None,
     "what": "a cut road through dense jungle, a wrecked ore hauler, the first bodies; isolation, ~25 s of driving"},
    {"id": "plant", "name": "Ore processing plant (collection plant)", "x": 1500, "y": -2500, "r": 4200, "z": 300,
     "key": "s_aerial.png",
     "what": "the gate camera (Miller hacks in), the hall of the dead (k_body), the runoff basin swim (k_basin), "
             "the drainage room fight (k_drainage); on foot inside"},
    {"id": "basin", "name": "Runoff basin", "x": 5500, "y": 2500, "r": 1600, "z": -350, "key": "k_basin.png",
     "what": "a sunken flooded basin at the plant's south side, half roofed; the swim under the hatches"},
    {"id": "field", "name": "The cleared field", "x": -8500, "y": -8500, "r": 5500, "z": 0, "key": None,
     "what": "a few hundred yards of cleared mud and stumps between the plant and the power plant: the open-ground "
             "fight, the FIRST SKAARJ in the open (it leaps at the bike); craters, haul trucks, pipe racks as cover"},
    {"id": "pit", "name": "The mine pit", "x": 13500, "y": -6500, "r": 6500, "z": -1800, "key": None,
     "what": "the open-pit mine the relic came out of: terraced benches, haul ramps, a broken drill rig with the "
             "snapped bit; the vehicle playground and an optional loop (Izarian nests)"},
    {"id": "power", "name": "Power plant", "x": -17500, "y": -15000, "r": 4000, "z": 200, "key": "s_miller.png",
     "what": "the generator building: Miller's barricaded security office (s_miller), his run out and death"},
    {"id": "shaft", "name": "Generator shaft", "x": -15500, "y": -16500, "r": 1500, "z": -2600, "key": "k_generator.png",
     "what": "down the shaft (s_generator): the control room restart, the Heavy Skaarj, the artifact at the bottom"},
    {"id": "pad", "name": "Marines' pickup pad", "x": -22500, "y": -24000, "r": 2700, "z": 400, "key": None,
     "what": "hold out with the bike until the speedship lands; 'You shoulda been a Marine'"},
]

# roads: [place ids or points], width in UU (the Manta is ~300 wide: 3 bikes abreast = ~1000)
ROADS = [
    {"id": "haul_w", "pts": ["lz", (-10500, 14000), (-6500, 8500), (-3000, 3000), "plant"], "w": 1100, "kind": "haul"},
    {"id": "haul_e", "pts": ["plant", (-2500, -6000), "field", (-13000, -12000), "power"], "w": 1300, "kind": "haul"},
    {"id": "pit_ramp", "pts": ["plant", (6500, -4500), (10500, -6000), "pit"], "w": 1000, "kind": "ramp"},
    {"id": "pit_back", "pts": ["pit", (12000, -16000), (2000, -21000), (-9000, -20000), "power"], "w": 1050, "kind": "track"},
    {"id": "pad_road", "pts": ["power", (-20500, -20000), "pad"], "w": 1100, "kind": "haul"},
    {"id": "jungle_loop", "pts": ["lz", (-22000, 12000), (-26000, 0), (-23000, -9000), "power"], "w": 1000, "kind": "track"},
]

# the beat spine (the three shipped maps' beats, in order, now places on one map) and how you get between them
BEATS = [
    ("lz", "arrival: search and rescue, no rough stuff", "foot -> Manta"),
    ("road_w", "the silent road: the hauler wreck, bodies, the plant's stack ahead", "drive 25 s"),
    ("plant", "the gate camera: Miller's one-way voice; the hall of the dead", "foot"),
    ("basin", "the runoff basin: a short swim", "swim"),
    ("plant", "the drainage room: chock-full of creatures", "foot fight"),
    ("field", "out into the open: TheSkaarjEncounter - the first Skaarj leaps at the bike", "Manta fight"),
    ("pit", "optional: the pit where the relic came from (nests, the broken drill)", "Manta loop"),
    ("power", "the generator building: Miller runs out against orders and dies", "foot, cutscene"),
    ("shaft", "the control room restart, the Heavy Skaarj, the artifact", "foot fight"),
    ("pad", "hold out until the Marines land", "Manta defence"),
]


def where(p):
    if isinstance(p, str):
        q = next(x for x in PLACES if x["id"] == p)
        return q["x"], q["y"]
    return p


def drive_seconds(speed=1100):
    out = {}
    for r in ROADS:
        pts = [where(p) for p in r["pts"]]
        out[r["id"]] = sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:])) / speed
    return out


def draw(png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig, ax = plt.subplots(figsize=(13, 13), facecolor="#0e130e")
    ax.set_facecolor("#16261a")
    ax.add_patch(plt.Rectangle((-WORLD, -WORLD), 2 * WORLD, 2 * WORLD, fill=False, ec="#557755", lw=2))
    col = {"haul": "#d8b060", "ramp": "#c08040", "track": "#9a8a60"}
    for r in ROADS:
        pts = [where(p) for p in r["pts"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", c=col[r["kind"]], lw=r["w"] / 120, alpha=0.8, solid_capstyle="round")
    for q in PLACES:
        if q["r"]:
            ax.add_patch(Circle((q["x"], q["y"]), q["r"], fc="#3a3a30" if q["id"] not in ("pit", "basin", "field") else
                                {"pit": "#4a3a28", "basin": "#1d3c5a", "field": "#3b3326"}[q["id"]], ec="#cccc99", lw=1, alpha=0.85))
        ax.text(q["x"], q["y"], q["name"] + ("\n[" + q["key"] + "]" if q["key"] else ""), color="#f0f0d0", ha="center", va="center", fontsize=8)
    for i, (pid, txt, how) in enumerate(BEATS):
        x, y = where(pid)
        ax.scatter(x + 900, y + 900, s=260, c="#b00000")
        ax.text(x + 900, y + 900, str(i + 1), color="white", ha="center", va="center", fontsize=9, weight="bold")
    secs = drive_seconds()
    ax.set_title("Sanctuary Open: site plan (beats 1-%d in red; roads by kind; key images in brackets)\n" % len(BEATS) +
                 "drive at 1100 UU/s: " + ", ".join("%s %.0f s" % kv for kv in secs.items()), color="#ddd", fontsize=9)
    ax.set_xlim(-WORLD - 500, WORLD + 500)
    ax.set_ylim(WORLD + 500, -WORLD - 500)
    ax.set_aspect("equal")
    ax.tick_params(colors="#777")
    fig.savefig(png, dpi=80, bbox_inches="tight", facecolor="#0e130e")


if __name__ == "__main__":
    draw(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_plan.png"))
    for k, v in drive_seconds().items():
        print("%-12s %4.0f s" % (k, v))
