"""Writes the first binder sheets (citizens + buildings). Run once; afterwards edit the .md files by hand.
    python binder/_seed.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CITIZENS = {
"hawkins": """id: hawkins
name: Cmdr. Hawkins
role: Authority sector commander, Avalon station
employer: authority
lives: tower
works: tower
routine: 0630 tower; 0800 tower; 1230 tower; 1300 tower; 1800 tower; 2200 tower
wants: a posting that matters; to be asked for anything by anyone
fears: that the sector could run without her and nobody would notice

Fifty-one. Twenty-six years in the Colonial Authority, the last six of them here. She came to Avalon as a
punishment she agreed with: she had signed a report about a company's private security that the company
did not like. The island is quiet because Liandri keeps it quiet. Her office is the long window on the top
floor; she stands at it more than she sits at the desk. She has never been to the plant. She has been
invited twice and declined twice, which the plant director understood perfectly.

She calls the patrols "the quietest patrol" with a straight face. She means it as a warning.
""",
"oduya": """id: oduya
name: Mira Oduya
role: Authority communications technician
employer: authority
lives: tower
works: tower
routine: 0600 tower; 0700 tower; 1900 tower; 2000 tower
wants: a transfer to a station with a real traffic board
fears: the weekly power cut coming during a real emergency

Twenty-nine. Watches a traffic board that only ever shows company flights: the cargo dropship from the
harbour pad, the rig shuttle at dawn and dusk. Eats in the tower mess, takes the one lift, has never been
down to the harbour, and is a little proud of that. Logs a complaint about the Thursday power cut every
week; the company has never answered one. Keeps the forms anyway, in order, in a drawer with nothing else
in it.
""",
"vask": """id: vask
name: Sgt. Teodor Vask
role: Authority pad crew and dropship pilot
employer: authority
lives: tower
works: authority_pad
routine: 0700 authority_pad; 1200 tower; 1300 authority_pad; 1500 dock; 1800 tower
wants: fuel that does not come with a company invoice
fears: the day the company refuses to sell it

Forty. Flies the station's one Atlantis dropship and keeps it alive with parts bought at the company
dock, at company prices, with a docking fee on top. The pad is the only Authority hardware outside the
tower and he treats it like a border. Knows every dock hand by first name because he has to.
""",
"reyes": """id: reyes
name: Jonah Reyes
role: Liandri rig hand
employer: liandri
lives: dorm
works: new_rig
routine: 0500 dorm; 0530 dock; 0600 new_rig; 1800 dock; 1830 dorm; 2000 dorm
wants: enough scrip converted to real money to leave
fears: the blowout that killed the old rig happening again on his shift

Thirty-three. Shuttle out from the dock at dawn, twelve hours on the new rig, shuttle back, dorm. Paid in
company scrip that is only worth anything at the company store. Sees the Authority people as tourists in a
tower; has never spoken to one. The old dead rig is on his horizon all day; the company says it is
harmless.
""",
"okafor": """id: okafor
name: Dr. Lena Okafor-Strand
role: Liandri plant director
employer: liandri
lives: directors_house
works: plant_office
routine: 0700 directors_house; 0800 plant_office; 1200 plant_office; 1700 hall_b; 1800 hall_a; 1900 directors_house
wants: the quarter's numbers; the hill behind her house kept green
fears: the sector office finding a reason to look closely

Forty-six. Runs the plant on a four-year rotation and intends to leave it bigger than she found it. Her
house is on the one hill left green, because she likes the view from it toward the sea and not toward the
tower. Walks the processing line at five every day; the hands know the time. Has invited the commander to
dinner twice.
""",
"benedek": """id: benedek
name: Catto Benedek
role: Liandri dock foreman
employer: liandri
lives: dorm
works: dock
routine: 0500 dock; 0600 cargo_pad; 0900 dock; 1400 cargo_pad; 1700 dock; 2000 dorm
wants: a crane that does not stop in the wind
fears: nothing he will say out loud; the boats that come to the old rig at night, privately

Fifty-five. Runs the dock, the crane and the cargo pad: everything the company owns that moves. Sells
Sergeant Vask his parts and charges him the docking fee without enjoying it. Knows exactly which boats
tie up at the dead rig after dark and has decided that this is not dock business.
""",
"arashiro": """id: arashiro
name: Sumi Arashiro
role: Liandri water and desalination technician
employer: liandri
lives: dorm
works: pump_house
routine: 0600 dorm; 0630 pump_house; 1000 water_tanks; 1300 pump_house; 1600 tank_farm; 1900 dorm
wants: a second pump so the first can be serviced
fears: the outfall stain reaching the intake

Thirty-eight. The whole island drinks what she makes: the plant, the dorm, and the tower, which pays for
it. The water tanks are the shore row; the pump house is the smallest building with the most pipes. Walks
the pipeline once a week looking for weeps. The stain in the sea by the outfall gets a little bigger each
year and is in none of her reports because it is in nobody's.
""",
"rook": """id: rook
name: Rook
role: smuggler, the dead rig
employer: outlaw
lives: dead_rig
works: boat_landing
routine: 2200 boat_landing; 2300 dead_rig; 0300 boat_landing; 0400 dead_rig; 1200 dead_rig
wants: the company to keep looking the other way
fears: a light on in the tower at three in the morning

Age unknown; says forty. Runs cargo nobody asks about through the decommissioned rig, which the company
left standing because removing it cost more. Buys fuel at the back of the dock through a foreman who is
not looking. One light burns on the dead rig at night, where there should be none: the third power,
visible from the commander's window if she knows to look.
""",
"hands": """id: hands
name: the processing line hands (twelve)
role: Liandri plant workers, two shifts
employer: liandri
lives: dorm
works: hall_a
routine: 0600 dorm; 0630 hall_a; 1230 hall_b; 1300 hall_a; 1830 dorm
wants: the night shift bonus back
fears: the silos

Not one person: the dozen who run Ore Hall A and the newer Hall B in two shifts. They come up from the dorm
by the back road, which is why the halls' personnel doors face the dorm and the roller doors face the silos
and the dock. Lunch is in Hall B's canteen corner. Nobody goes near the dead hall on the slope.
""",
}

# at: along across yaw-of-the-front (world degrees). The look is 300; the shore runs across at along ~17500.
BUILDINGS = {
"tower": """id: tower
name: The Authority tower
owner: authority
layer: core
kind: tower
at: 0 0 300
size: 36 36 110
users: hawkins oduya vask
doors: front:personnel
roof: none
wear: 0.5
lit: no
ref: tower

The tallest building on the island and the poorest. Old concrete, few lights. Built by the first charter
survey before Liandri came; the company let the Authority keep it because it was useless to them. Runs on
company power through the one pylon line.
""",
"authority_pad": """id: authority_pad
name: Authority landing pad
owner: authority
layer: core
kind: pad
at: 1800 900 300
size: 40 40 2
users: vask hawkins
doors:
roof: none
wear: 0.4
lit: yes
ref: pad

One small pad, one old Atlantis dropship, one antenna. The company charges docking fees for it.
""",
"plant_office": """id: plant_office
name: Liandri plant office
owner: liandri
layer: boom
kind: office
at: 12400 300 120
size: 18 12 9
users: okafor
doors: front:personnel right:personnel
roof: flat
wear: 0.05
lit: yes
ref: processing_hall

The only clean concrete on the island. Two storeys, a window strip toward the sea and none toward the
tower. The director walks out of its right door at five to start along the processing line.
""",
"hall_a": """id: hall_a
name: Ore Hall A
owner: liandri
layer: core
kind: hall
at: 13900 -700 30
size: 30 14 8
users: hands okafor
doors: front:roller left:personnel right:roller
bays: front
roof: sawtooth
wear: 0.35
lit: yes
ref: processing_hall

The first hall, from the landing years: ore comes in from the silos on the right by roller door, product
goes out the front bay toward the dock. The hands come in from the dorm by the left personnel door. Patched
panels, the oldest sawtooth roof.
""",
"hall_b": """id: hall_b
name: Processing Hall B
owner: liandri
layer: boom
kind: hall
at: 15300 1500 30
size: 36 16 11
users: hands okafor
doors: front:roller left:personnel back:roller
bays: front back
roof: sawtooth
wear: 0.1
lit: yes
ref: processing_hall

The boom-time hall, bigger and lit; the canteen corner is in its left end where the personnel door is.
Product in from the pipeline side (back), out the front to the dock road.
""",
"hall_c": """id: hall_c
name: the dead hall
owner: nobody
layer: decline
kind: hall
at: 12200 -2700 75
size: 22 12 7
users:
doors: front:roller
roof: pitched
wear: 0.85
lit: no
abandoned: yes
ref: processing_hall

The second hall of the landing years, on the slope. Closed after the blowout took the old rig's supply;
never reopened, never pulled down. Roof panels gone, roller door jammed half up. Nobody goes near it.
""",
"silos": """id: silos
name: Ore silos
owner: liandri
layer: boom
kind: silo
at: 15500 -1900 30
size: 9 9 22
count: 3 across
users: hands
doors:
roof: cone
wear: 0.3
lit: yes
ref: ore_tank

Three rust silos in a row along the shore axis, feeding Hall A's right roller door by conveyor. The hands
fear them: a man went in one in the boom years.
""",
"tank_farm": """id: tank_farm
name: Product tank farm
owner: liandri
layer: boom
kind: tank
at: 13200 1900 30
size: 13 13 16
count: 2x2
users: arashiro hands
doors:
roof: dome
wear: 0.15
lit: yes
ref: storage_tank

Four pale product tanks between the halls and the cooling towers, with a ladder each and the pipeline's
origin at their feet.
""",
"cooling_towers": """id: cooling_towers
name: Cooling towers
owner: liandri
layer: boom
kind: tower
at: 14700 3300 45
size: 14 14 34
count: 2 along
users: hands
doors: front:personnel
roof: none
wear: 0.1
lit: yes
ref: cooling_tower

The tallest things in the plant, still far below the Authority's tower. Steam when the line runs.
""",
"generator_house": """id: generator_house
name: Generator house
owner: liandri
layer: boom
kind: hall
at: 15700 2400 300
size: 16 10 7
users: hands
doors: front:roller left:personnel
roof: flat
wear: 0.2
lit: yes
ref: processing_hall

Where the island's power comes from, including the tower's; the pylon line starts at its back wall.
""",
"pump_house": """id: pump_house
name: Pump house
owner: liandri
layer: core
kind: pump
at: 17100 -1300 300
size: 8 6 5
users: arashiro
doors: front:personnel
roof: flat
wear: 0.4
lit: yes
ref: processing_hall

The smallest building with the most pipes: the sea intake on the shore side, the desalination stacks, the
feed to the water tanks. Arashiro's door faces the dorm road.
""",
"water_tanks": """id: water_tanks
name: Water tanks
owner: liandri
layer: core
kind: tank
at: 16900 -2300 300
size: 9 9 10
count: 3 across
users: arashiro
doors:
roof: dome
wear: 0.45
lit: no
ref: storage_tank

The shore row, older and smaller than the product tanks, grey not pale.
""",
"dorm": """id: dorm
name: Company dormitory
owner: liandri
layer: core
kind: dorm
at: 12700 -1600 120
size: 24 10 7
users: reyes benedek arashiro hands
doors: front:personnel back:personnel
roof: flat
wear: 0.3
lit: yes
ref: processing_hall

Two storeys of bunk rooms for everyone the company pays in scrip. Its front door faces the back road to the
halls; its back door faces the dock path. Window strips on both long sides.
""",
"directors_house": """id: directors_house
name: The director's house
owner: liandri
layer: boom
kind: house
at: 10600 -4200 300
size: 14 10 6
users: okafor
doors: front:personnel
roof: flat
wear: 0.0
lit: yes
ref: processing_hall

On the one hill left green, looking at the sea and not at the tower.
""",
"cargo_pad": """id: cargo_pad
name: Company cargo pad
owner: liandri
layer: boom
kind: pad
at: 16400 -3400 300
size: 50 50 2
users: benedek
doors:
roof: none
wear: 0.1
lit: yes
ref: pad

The big pad: the boxy company dropship, floodlights, the product off-world. Vask's pad fits in one corner
of it.
""",
"dock": """id: dock
name: The dock
owner: liandri
layer: boom
kind: dock
at: 19300 6200 300
size: 130 22 6
users: benedek reyes vask
doors:
roof: none
wear: 0.2
lit: yes
ref: dock_crane

The long quay into the sea with the crane, the rig shuttle's berth at its end and the containers along it.
""",
"boat_landing": """id: boat_landing
name: the old boat landing
owner: nobody
layer: decline
kind: jetty
at: 18300 -5300 300
size: 30 6 3
users: rook
doors:
roof: none
wear: 0.8
lit: no
ref: dock_crane

A rotten timber jetty west of the plant, from before the dock. Boats to the dead rig leave from here after
dark; the company has not noticed, officially.
""",
"new_rig": """id: new_rig
name: The new rig
owner: liandri
layer: boom
kind: rig
at: 22500 6800 0
size: 26 32 38
users: reyes
doors:
roof: none
wear: 0.1
lit: yes
ref: drilling_rig

Where the money is now. A flare burns at its top.
""",
"dead_rig": """id: dead_rig
name: The dead rig
owner: nobody
layer: decline
kind: rig
at: 22500 17000 20
size: 26 32 38
users: rook
doors:
roof: none
wear: 0.9
lit: no
abandoned: yes
ref: dead_rig

Decommissioned after the blowout and never removed, because that was cheaper. One light at night where
there should be none.
""",
"company_mast": """id: company_mast
name: Liandri comms mast
owner: liandri
layer: boom
kind: mast
at: 1000 -15400 0
size: 6 7 30
users: okafor
doors:
roof: none
wear: 0.1
lit: yes
ref: radio_mast

On the west hill, taller than the Authority's antenna.
""",
}

for d, items in (("citizens", CITIZENS), ("buildings", BUILDINGS)):
    os.makedirs(os.path.join(HERE, d), exist_ok=True)
    for k, text in items.items():
        p = os.path.join(HERE, d, k + ".md")
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(text)
            print("wrote", p)
