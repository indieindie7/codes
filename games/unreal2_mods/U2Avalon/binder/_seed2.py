"""Second seeding: populating the island and the waters (user, 2026-10-06: "populate the island and nearby
waters with our assets ... road generation ... pipes with factories"). Run once; then edit the .md by hand.
    python binder/_seed2.py
Positions are (along, across, front yaw) in the look frame; the plant shelf is along 11500..17500, across
+-5100, the shore at ~17500, the dock at (19300, 6200).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CITIZENS = {
"nkemelu": """id: nkemelu
name: Pvt. Ada Nkemelu
role: Authority gate guard, the tower road checkpoint
employer: authority
lives: tower
works: checkpoint
routine: 0600 tower; 0630 checkpoint; 1400 tower; 1430 checkpoint; 2200 tower
wants: one vehicle a day that is not the company's
fears: being told to wave the wrong one through

Twenty-three. Stands in a hut on the only road up to the tower and logs every company truck that passes,
because the regulations say so and nobody reads the log. Knows Benedek's drivers by their horns.
""",
"haldane": """id: haldane
name: Rab Haldane
role: Liandri depot clerk and pipeline walker
employer: liandri
lives: dorm
works: fuel_depot
routine: 0600 dorm; 0630 fuel_depot; 0900 pump_station; 1100 shed_a; 1300 fuel_depot; 1600 shed_b; 1900 dorm
wants: the sheds along the line to get doors that close
fears: the weep at kilometre three turning into a leak

Forty-four. Keeps the fuel depot's book and walks the pipeline on alternate days: pump station, the two
maintenance sheds, the intake. Has reported the same weep for two years. Keeps a kettle in shed B.
""",
}

BUILDINGS = {
# --- land: the plant's outliers, along the pipeline and the roads ---
"fuel_depot": """id: fuel_depot
name: Fuel depot
owner: liandri
layer: boom
kind: tank
at: 15900 -4400 300
size: 7 7 9
count: 2 across
mesh: storage_tank_2_kiln
users: haldane benedek vask
doors:
roof: dome
wear: 0.3
lit: yes
ref: storage_tank

Two squat fuel tanks by the cargo pad: the dropships' and the dock's fuel, and the Authority's, at a price.
""",
"pump_station": """id: pump_station
name: Pipeline pump station
owner: liandri
layer: boom
kind: pump
at: 16800 2600 30
size: 7 5 4
users: haldane arashiro
doors: front:personnel
roof: flat
wear: 0.35
lit: yes
ref: processing_hall

A booster pump on the line between the generator house and the shore: pipes in, pipes out, one lamp.
""",
"shed_a": """id: shed_a
name: Maintenance shed A
owner: liandri
layer: boom
kind: hall
at: 18000 4600 300
size: 8 6 4
users: haldane
doors: front:roller
roof: flat
wear: 0.5
lit: no
ref: processing_hall

A tin shed by the pipeline where it meets the shore road: spares, a winch, a door that does not close.
""",
"shed_b": """id: shed_b
name: Maintenance shed B
owner: liandri
layer: core
kind: hall
at: 11800 2800 120
size: 8 6 4
users: haldane
doors: front:roller
roof: pitched
wear: 0.6
lit: no
ref: processing_hall

The older shed at the plant's back fence, from the landing years; Haldane's kettle lives here.
""",
"checkpoint": """id: checkpoint
name: Authority checkpoint
owner: authority
layer: core
kind: house
at: 4200 -300 120
size: 6 5 3.5
users: nkemelu
doors: front:personnel
roof: flat
wear: 0.45
lit: yes
ref: processing_hall

A hut on the tower road where it leaves the plant's side of the hill: a barrier, a lamp, a log nobody reads.
""",
"old_camp": """id: old_camp
name: the first camp
owner: nobody
layer: decline
kind: house
at: 10200 -3200 60
size: 7 5 3.5
count: 2 across
users:
doors: front:personnel
roof: pitched
wear: 0.9
lit: no
abandoned: yes
ref: processing_hall

Two prefab huts from the survey years on the slope above the dead hall, roofs gone, the company's first
address on Avalon. Nobody has lived here since the dorm went up.
""",
"beacon": """id: beacon
name: Harbour beacon
owner: liandri
layer: core
kind: mast
at: 19800 -3800 300
size: 3 3 14
mesh: radio_mast_2_kiln
users: benedek reyes
doors:
roof: none
wear: 0.5
lit: yes
ref: radio_mast

A short lattice beacon on the rocks west of the dock, for the rig shuttle coming home in the dark.
""",
"intake": """id: intake
name: Sea-water intake
owner: liandri
layer: core
kind: pump
at: 17900 -1600 300
size: 5 4 3
users: arashiro
doors: front:personnel
roof: flat
wear: 0.5
lit: no
ref: processing_hall

The desalination intake on the shore below the pump house: a box over the pipe that goes into the sea.
""",
# --- water: wellheads, the barge, the wreck ---
"wellhead_a": """id: wellhead_a
name: Wellhead A
owner: liandri
layer: boom
kind: rig
at: 21500 1200 40
size: 14 16 22
card: DrillingRigHY 2400
users: reyes
doors:
roof: none
wear: 0.2
lit: yes
ref: drilling_rig

A small unmanned wellhead platform between the shore and the new rig; the shuttle checks it at dawn.
""",
"wellhead_b": """id: wellhead_b
name: Wellhead B
owner: liandri
layer: boom
kind: rig
at: 24500 -2800 10
size: 14 16 22
card: DrillingRigHY 2400
users: reyes
doors:
roof: none
wear: 0.25
lit: yes
ref: drilling_rig

The second wellhead, further out and west.
""",
"wellhead_old": """id: wellhead_old
name: the capped well
owner: nobody
layer: decline
kind: rig
at: 23800 11500 70
size: 12 14 18
card: DeadRigHY 2000
users:
doors:
roof: none
wear: 0.9
lit: no
abandoned: yes
ref: dead_rig

The first well, capped after the blowout, leaning; between the dead rig and the dock.
""",
"barge": """id: barge
name: Company barge
owner: liandri
layer: boom
kind: barge
at: 20400 7400 300
size: 40 12 4
users: benedek reyes
doors:
roof: none
wear: 0.3
lit: yes
ref: dock_crane

The flat barge that takes product and containers from the quay to the ships that never come closer.
""",
"wreck": """id: wreck
name: the supply ship
owner: nobody
layer: decline
kind: wreck
at: 18400 -7600 250
size: 30 12 8
users:
doors:
roof: none
wear: 1.0
lit: no
abandoned: yes
ref: cargo_dropship

The transport that brought the first camp, run aground on the western rocks and stripped; the company's
first address on the island is a hull.
""",
}

for d, items in (("citizens", CITIZENS), ("buildings", BUILDINGS)):
    for k, text in items.items():
        p = os.path.join(HERE, d, k + ".md")
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(text)
            print("wrote", p)
