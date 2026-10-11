# Rules from building practice and the literature

Rules of thumb, written in our own words from well-known sources. They vary by country and
building code. They're for making game buildings read as real, not for real construction.

## Human scale

- **Doors:** interior 0.8 to 0.9 m wide (ResPlan median 0.86 m), entrance doors wider (about 0.9 to
  1.0 m), about 2.0 to 2.1 m tall. Double or sliding doors to balconies run 1.2 to 1.8 m.
- **Corridors:** 0.9 m is tight, 1.0 to 1.2 m is comfortable, and two people pass at about
  1.2 to 1.5 m. A wheelchair turns in a 1.5 m circle.
- **Ceilings:** homes are about 2.4 to 2.7 m, older and grander buildings 3 m or more. Codes often
  set about 2.3 to 2.4 m as the minimum for living rooms. Offices and shops are 2.7 to 3.5 m,
  plus a floor and ceiling build-up of 0.3 to 0.6 m per storey.
- **Storey height** (floor to floor): about 2.8 to 3.2 m for homes, 3.5 to 4.5 m for offices.
- **Stairs** (Blondel's rule, 1675):
  - two risers plus one tread come to about 60 to 65 cm, one stride;
  - homes use risers of 15 to 18 cm and treads of 25 to 30 cm, with at least 2.0 m of headroom;
  - a straight flight has about 12 to 16 steps before a landing.
- **Windows:**
  - sill about 0.8 to 1.0 m (lower for a view, higher in kitchens and bathrooms);
  - head at about 2.1 m;
  - daylight reaches about 2 to 2.5 times the window head's height into the room, so rooms
    deeper than about 5 to 6 m need light from a second side.
- **Kitchen:** the "work triangle" (sink, stove, fridge) has a total length of about 4 to 8 m.
  Worktops are about 0.9 m high and 0.6 m deep.
- **Room minimums** (typical codes, roughly): a bedroom of about 7 m² for one person and 10 m² for
  two, at least about 2.4 m across. ResPlan's medians are 14.6 m² and 3.5 m across.

## Layout (Alexander, *A Pattern Language*, 1977, paraphrased)

- **Intimacy gradient:** public rooms near the entrance, private ones deep. ResPlan shows it:
  bathrooms and balconies sit a step deeper than kitchens and living rooms, often reached
  through a bedroom.
- **Entrance transition:** a change of light, level or direction between the street and the
  inside.
- **Light on two sides of every room:** rooms lit from two sides feel better and get used more.
- **Common areas at the heart, small rooms off them.** In ResPlan the living area is the hub:
  the front door opens into it, and bedrooms and the kitchen open off it.
- **Thick walls and alcoves, a window place, a ceiling height that varies with room size.**

## Buildings in a city (Lynch, *The Image of the City*, 1960, paraphrased)

People read a city by five things:
- **paths** (streets they move along);
- **edges** (walls, rivers, rail lines that stop movement);
- **districts** (areas with one character);
- **nodes** (squares and junctions where paths meet);
- **landmarks** (things seen from afar, used to find the way).

A game town needs all five to be learnable.

## Making facades by rules (shape grammars)

Müller, Wonka et al., *Procedural Modeling of Buildings* (SIGGRAPH 2006), and Wonka et al.,
*Instant Architecture* (2003), describe the same steps:

1. **Mass:** simple volumes for the building's shape.
2. **Facades:** each side split into floors.
3. **Bays:** each floor split into repeated "tiles".
4. **Elements:** each tile gets a window, door or wall panel.

Rules pick by context (ground floor different, corners different, the top floor set back). This
gives believable variety with a few rules. It's how CityEngine builds cities; BuildingNodes for
Blender (open source) does a node version.

## Game scale

- Real sizes feel cramped in games. The camera sits at the eye, the player's collision cylinder is
  wide, and third-person cameras need room.
- Many games enlarge interiors by about 1.2 to 1.5 times, doors most of all, and keep stairs and
  furniture closer to real size so they still read.
- For Unreal II: measure the player pawn's CollisionRadius and CollisionHeight (U2Pilot
  `dump`, or U2TestHub `hub info`), and a few doorways in stock maps, before choosing the factor.
  The repo's U2Blender scale is 1 m = 50 uu.
