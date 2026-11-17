# ColoradoLightning

ColoradoLightning brings FH1-inspired muted golden daytime midtones and warmer sunlight to Forza Horizon 2. It uses FH2's native dry-day color grade and adjusts the sunlight and reflected sunlight curves on the mainland and Storm Island. The wet and night grading maps retain their stock values. Both chase cameras use a subtle vignette at all speeds and times of day.

## Install

Requires Azimuth and FH2 Mod Platform 2.9.0. Extract the release ZIP beside azimuth.exe so the DLL is at fh2-mods/ColoradoLightning.dll. Restart Azimuth. Under Pause > MODS > YOUR MODS, ColoradoLightning has the standard load switches. The mod is eligible to load online and the platform checks GitHub releases from suderek22/FH2_ColoradoLightning.

To uninstall, remove the DLL and restart Azimuth. The platform manages cleanup of its overrides. Mods that replace the same DryDay, TimeOfDay FXB, or CameraPhysics files can conflict. The platform reports file ownership in fh2-mods/platform.log.

## Build

Use CMake, a Windows x64 C++ toolchain with a resource compiler, and Python 3. Extract fh2-platform-v2.9.0-source.zip and point CMake at the inner source folder. FH2_MOUNT points to the game Mount folder containing media. The build derives and embeds the modified assets from that installation.

```powershell
cmake -S . -B build -A x64 -DFH2_PLATFORM_SOURCE=<platform-source> -DFH2_MOUNT=<game-Mount>
cmake --build build --config Release --target ColoradoLightning
cmake --install build --config Release --prefix dist/ColoradoLightning_v1.0.1
```

Version 1.0.1 reduces the yellow cast in grass and lowers daytime brightness based on the supplied comparison screenshots. In-game visual validation of the revised preset is pending. Compare the same mainland chase-camera view with the mod enabled and disabled around noon, then check night and rain separately.
