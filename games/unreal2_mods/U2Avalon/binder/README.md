# The Avalon binder

Yu Suzuki kept a binder of biographies for every Shenmue NPC, most of it never shown. This is ours, and it
also DRIVES the generation: the building sheets place and shape the Liandri plant (make_avalon.py reads
them), the citizen sheets bound what gets built (every building needs users, every routine needs places),
and check_binder.py refuses a layout that breaks either.

Format: markdown, one file per person or building. The header is `key: value` lines up to the first blank
line (machine-read); below it, prose for people (never read by code, always read by us).

Building header keys (binder/buildings/*.md):

    id: hall_a                  stable name, used by citizens and the generator
    name: Ore Hall A            display name
    owner: liandri | authority | nobody
    layer: core | boom | decline       when it was built (the growth rings)
    kind: hall | tank | silo | tower | office | dorm | pad | dock | rig | house | mast | pump | jetty
    at: 13800 -600 30           along, across (world units in the look frame from the tower, 300 degrees) and the
                                yaw the FRONT faces (degrees, world)
    size: 30 14 8               footprint width, depth, height in metres (parts are metric; 1 m = 50 units)
    users: oduya hawkins        citizen ids who use it (empty for an abandoned thing: say abandoned: yes)
    doors: front:roller back:personnel left:airlock    door types per side (front back left right)
    bays: front                 loading bays (sides)
    roof: flat | sawtooth | pitched | dome | none
    wear: 0.0-1.0               0 new, 1 rotten (missing panels, rust swatch, no lights)
    lit: yes | no               has working lights (glow strips)
    abandoned: yes              (optional)
    ref: processing_hall        which ref sheet / scripted type it answers to for the silhouette check

Citizen header keys (binder/citizens/*.md):

    id: oduya
    name: Mira Oduya
    role: Authority communications technician
    employer: authority | liandri | outlaw
    lives: tower                 building id
    works: tower                 building id
    routine: 0600 tower_mess; 0700 tower; 1900 tower_mess; 2100 tower    "HHMM building_id" pairs
    headcount: 12                a group sheet (the hands): how many walk each routine trip (default 1)
    wants: ...
    fears: ...

Rules the checker enforces (check_binder.py):
1. every building in a routine exists; 2. every non-abandoned building has at least one user;
3. a building's doors face the side its users come from (the checker suggests the side from the
   routine's previous place); 4. an abandoned building has wear >= 0.6 and lit: no; 5. the growth
   rings make sense: a core building is nearer the old pad than a boom building of the same kind.

Systems keys (optional, read by tools/systems.py; defaults by id/kind live in that file):

    provides: ore               resources the building puts into the town: ore power water fuel cooling workers goods comms supply
    needs: power water workers  resources it must get from a provider within reach (ore 220 m conveyor, power 350 m cable,
                                water 300 m pipe, fuel 180 m, cooling 160 m, workers/goods/supply by road 450-500 m, comms 1500 m)

A layout is a town only when every core need (ore, power, water, workers) is met; systems.py routes the
connections and writes them into the layout JSON for the build step.
