#include "fh2mod.h"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace {
struct Override {
    int resource_id;
    const char* path;
};

constexpr Override overrides[] = {
    {101, "PostEffects/ColourGradingMaps/DryDay.swatchbin"},
    {102, "timeofday/xboxone/TimeOfDay.fxb"},
    {103, "timeofday/xboxone/TimeOfDay_island.fxb"},
    {104, "Camera/CameraPhysics.xml"},
};

HMODULE module;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        module = instance;
    }
    return TRUE;
}

FH2MOD_EXPORT int fh2mod_init(const FH2ModApi* api) {
    if (!api || api->api_version < 10) {
        return 1;
    }

    FH2ModInfo info{};
    info.size = sizeof info;
    info.name = "ColoradoLightning";
    info.version = MOD_VERSION;
    info.github_repo = "suderek22/FH2_ColoradoLightning";
    info.platform_version = FH2MOD_PLATFORM_VERSION;
    info.check_updates = 1;
    info.description = "Muted golden daylight and a soft chase-camera vignette.";
    info.offline_only = 0;
    FH2Mod* mod = api->register_mod(&info);
    if (!mod) {
        return 1;
    }

    for (const auto& asset : overrides) {
        HRSRC resource = FindResourceW(module, MAKEINTRESOURCEW(asset.resource_id), MAKEINTRESOURCEW(10));
        HGLOBAL loaded = resource ? LoadResource(module, resource) : nullptr;
        const void* bytes = loaded ? LockResource(loaded) : nullptr;
        DWORD size = resource ? SizeofResource(module, resource) : 0;
        if (!bytes || !size || !api->set_file(mod, asset.path, bytes, size)) {
            api->log(mod, "Could not register this render override:");
            api->log(mod, asset.path);
        }
    }
    return 0;
}
