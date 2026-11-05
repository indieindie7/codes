// BepInEx 5 preloader patcher: Core Keeper (Unity 6) assemblies reference netstandard 2.1;
// with the game's Cecil 0.11 in BepInEx/core the resolver fails to find it when the
// Chainloader entrypoint patch is written. Point the resolver at the game's Managed dir.
using System.Collections.Generic;
using System.IO;
using BepInEx;
using BepInEx.Bootstrap;
using Mono.Cecil;

public static class CKResolveFix
{
    public static IEnumerable<string> TargetDLLs { get { yield return "UnityEngine.CoreModule.dll"; } }
    // AssemblyPatcher writes the patched module with the resolver it was READ with, not TypeLoader's.
    public static void Patch(AssemblyDefinition a)
    {
        if (a.MainModule.AssemblyResolver is BaseAssemblyResolver r) Hook(r);
    }
    static void Hook(BaseAssemblyResolver r)
    {
        // BepInEx's own fallback handler does not fire with the game's Cecil 0.11, so plugins
        // (which reference BepInEx.dll in core) are silently skipped: "0 plugins to load".
        string[] dirs = { Paths.ManagedPath, Paths.BepInExAssemblyDirectory, Paths.PluginPath };
        foreach (var d in dirs) r.AddSearchDirectory(d);
        r.ResolveFailure += (s, name) =>
        {
            foreach (var d in dirs)
            {
                var f = Path.Combine(d, name.Name + ".dll");
                if (File.Exists(f)) return AssemblyDefinition.ReadAssembly(f);
            }
            return null;
        };
    }
    public static void Initialize()
    {
        Hook(TypeLoader.Resolver);
    }
}
