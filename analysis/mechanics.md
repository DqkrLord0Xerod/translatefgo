# TranslateFGO Installer Mechanics Recon

## License Attribution
- The repository distributes the application under the MIT License and requires retention of the copyright notice and permission statement in derivative works (`LICENCE.txt`).
- The README reiterates the MIT license for the app and clarifies that bundle creation, translation, and API code are private while the installer is open source (`README.md`).

## Core Components Overview
- `RayshiftTranslateFGO/Views/InstallerPage.xaml.cs` drives the translation installer UI, decides filesystem mode, loads bundles via API handshakes, and orchestrates install/update/uninstall actions.
- `RayshiftTranslateFGO.Android/Services/ContentManager.cs` implements filesystem access for direct storage, Storage Access Framework (SAF), and Shizuku/NextGenFS, including file read/write/delete helpers and discovery of installed game directories.
- `RayshiftTranslateFGO.Android/Services/ScriptManager.cs` encapsulates script installation logic: refreshing handshakes, downloading bundles, validating hashes, updating `assetstorage.txt`, and writing/removing files through `ContentManager`.
- `RayshiftTranslateFGO/Services/RestfulAPI.cs` provides API clients for handshake, bundle download, asset list updates, and telemetry callbacks.
- `RayshiftTranslateFGO.Android/Services/IntentService.cs` manages SAF intents, MediaProjection prompts, and Shizuku binding/permission flows that gate certain filesystem operations.
- `RayshiftTranslateFGO/Util/AppNames.cs` defines the package names checked when scanning external storage for FGO data folders, ensuring the installer only touches recognized JP client directories.

## Sequence Diagrams

### Filesystem Mode Selection
```mermaid
sequenceDiagram
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    participant INT as IntentService.cs
    UI->>Pref: Load saved SAF tree URIs / Shizuku flag
    UI->>CM: CheckBasicAccess()
    alt Direct access succeeds
        UI->>UI: Set mode = DirectAccess
    else Direct access fails
        UI->>Pref: Read UseShizuku toggle
        alt Shizuku preferred
            UI->>INT: IsShizukuAvailable()
            INT-->>UI: Binder availability
            alt Binder ready
                UI->>UI: Set mode = Shizuku
            else Binder absent
                INT->>INT: BindShizuku()
                UI->>UI: Wait/retry until bound or timeout
            end
        else SAF fallback
            UI->>UI: Set mode = StorageFramework
        end
    end
```

### Update (Translation List Refresh)
```mermaid
sequenceDiagram
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    participant REST as RestfulAPI.cs
    UI->>Pref: Load persisted SAF tree URIs
    UI->>CM: GetInstalledGameApps(mode, storageLocations)
    CM-->>UI: Installed JP client paths with assetstorage metadata
    loop For each detected install
        UI->>CM: GetFileContents(mode, assetstorage.txt)
        CM-->>UI: Base64 assetstorage payload + timestamp
    end
    UI->>REST: GetHandshakeApiResponse(region, latest assetstorage)
    REST-->>UI: Translation list + asset status + telemetry flags
    UI->>UI: Update donor/login state, schedule info, and GUI bindings
    UI->>UI: Call ProcessAssets(...) to build bundle status table
```

### Installation Flow
```mermaid
sequenceDiagram
    participant User
    participant UI as InstallerPage.xaml.cs
    participant SM as ScriptManager.cs
    participant REST as RestfulAPI.cs
    participant CM as ContentManager.cs
    User->>UI: Tap Install bundle
    UI->>User: Confirmation dialog (size warning)
    alt User confirms
        UI->>SM: InstallScript(mode, region, installPaths, bundleId)
        SM->>REST: GetHandshakeApiResponse(region, assetStorage)
        REST-->>SM: Latest bundle metadata
        SM->>REST: GetScript(downloadUrl) for each file (parallel)
        REST-->>SM: Script bytes
        SM->>SM: Verify SHA-1 checksums & stage files
        opt Bundle requires extra assets
            SM->>CM: GetFileContents(mode, extra paths) for packaging
            SM->>AsyncUploader: Upload extras & await transformed data
        end
        SM->>REST: SendAssetList(updated assetstorage)
        REST-->>SM: Replacement assetstorage blob
        SM->>CM: RemoveFileIfExists(mode, *.bin)
        SM->>CM: WriteFileContents(mode, translated scripts & assetstorage)
        SM-->>UI: ScriptInstallStatus(success, message)
        UI->>REST: SendSuccess telemetry (async)
        UI->>UI: Refresh translation list
    else User cancels
        UI->>UI: Abort install
    end
```

### Uninstallation Flow
```mermaid
sequenceDiagram
    participant User
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    User->>UI: Tap Uninstall
    UI->>User: Confirmation dialog
    alt User confirms
        UI->>Pref: Load cached bundle manifest & extra purge list
        UI->>UI: Enumerate installed bundle file names (scripts + extras)
        loop Files to remove
            UI->>CM: RemoveFileIfExists(mode, filePath)
            CM-->>UI: Deletion result
        end
        UI->>Pref: Clear InstalledScript_* and UninstallPurgesExtras_* keys
        UI->>UI: Update status text & refresh list
    else User cancels
        UI->>UI: Abort uninstall
    end
```

## Data Location Detection
- Direct access enumerates each external storage root, walks parent directories, and collects folders whose final segment matches `AppNames.ValidAppNames` (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- SAF mode uses persisted tree URIs gathered during onboarding to query child folders via `DocumentFile` APIs before matching valid package names (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- Shizuku mode lists directories using `NextGenFSServiceConnection` bindings for elevated access, falling back to manual path probes when necessary (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`, `RayshiftTranslateFGO.Android/NextGenFSServiceConnection.cs`, `RayshiftTranslateFGO.Android/MainActivity.cs`).
- Initial onboarding screens leverage process lists to suggest package identifiers and collect SAF permissions (`RayshiftTranslateFGO/Views/PreInitializePage.xaml.cs`).

## Error & Update Handling
- Asset status warnings triggered by the handshake (e.g., missing, out-of-date, corrupt) result in user-facing alerts before any installation occurs (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`).
- Install exceptions such as permission errors, checksum mismatches, or missing extra assets short-circuit the flow with descriptive error strings propagated back to the UI (`RayshiftTranslateFGO.Android/Services/ScriptManager.cs`).
- `ContentManager` centralizes error handling for SAF and Shizuku operations, surfacing status codes that drive retry prompts or onboarding redirects (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
