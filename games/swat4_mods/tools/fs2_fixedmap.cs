// SwatMinds gym: fixed FS2 skirmish map. $smMapFile = "" -> stock random map;
// a name -> %APPDATA%\FrozenSynapse2\smmaps\<name>.enc: the first start saves its
// encounter there, later starts load it (same layout + deployment each match).
package SMFixedMap {
   function startSkirmish(%setup, %enc) {
      if ($smMapFile !$= "") {
         %f = getPrefsPath("smmaps/" @ $smMapFile @ ".enc");
         if (isFile(%f)) {
            %e = new ScriptEncounter();
            %e.loadEncounter(%f);  // void; fills %e (the global form returns nothing)
            %enc = %e;
            echo("SMFIXED load " @ %f @ " -> " @ %e);
         } else {
            saveEncounter(%f, %enc);
            echo("SMFIXED save " @ %f @ " " @ isFile(%f));
         }
      }
      return Parent::startSkirmish(%setup, %enc);
   }
};
activatePackage(SMFixedMap);  // exec once per game run: a re-exec breaks Parent::
