id: tank_farm
name: Concentrate tank farm
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
mesh: storage_tank_1_kiln
pipes: pump_station
provides: conc
needs: power
ref: storage_tank

Four pale tanks of concentrate slurry, agitated, below hall_b's flotation floor, with a ladder each and the
slurry pipeline's origin at their feet. Not fuel (engineer 2026-10-09): the only fire set-back case is the
fuel depot. The conc chain in systems.py runs hall_b -> here -> the pump station -> the concentrate shed at
the dock.
