# TranslateFGO Installer Mechanics Recon

## License Attribution
- The repository distributes the application under the MIT License and requires retention of the copyright notice and permission statement in derivative works (`LICENCE.txt`).
- The README reiterates the MIT license for the app and clarifies that bundle creation, translation, and API code are private while the installer is open source (`README.md`).

## Core Components Overview
- `RayshiftTranslateFGO/Views/InstallerPage.xaml.cs` drives the translation installer UI, negotiates filesystem mode, performs handshake requests, and orchestrates install/update/uninstall actions.
- `RayshiftTranslateFGO.Android/Services/ContentManager.cs` implements filesystem access strategies for direct storage, Storage Access Framework (SAF), and Shizuku/NextGenFS, including file discovery, read/write/delete helpers, and detection of installed game directories.
- `RayshiftTranslateFGO.Android/Services/ScriptManager.cs` encapsulates bundle installation logic: refreshing handshakes, downloading archives, validating checksums, updating `assetstorage.txt`, and writing or removing files via `ContentManager`.
- `RayshiftTranslateFGO/Services/RestfulAPI.cs` provides the network API client used for handshake metadata, bundle downloads, asset list refreshes, and telemetry callbacks.
- `RayshiftTranslateFGO.Android/Services/IntentService.cs` manages SAF intents, MediaProjection/storage prompts, and Shizuku binding/permission flows that gate filesystem operations.
- `RayshiftTranslateFGO/Util/AppNames.cs` defines valid package identifiers used when scanning storage to ensure only known JP client directories are targeted.
- `RayshiftTranslateFGO/Views/PreInitializePage.xaml.cs` and related onboarding views collect SAF permissions, Shizuku opt-ins, and cached storage URIs before the installer runs.

## Sequence Diagrams

### Filesystem Mode Selection
```mermaid
sequenceDiagram
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    participant INT as IntentService.cs
    UI->>Pref: Load saved SAF tree URIs / Shizuku toggle
    UI->>CM: CheckBasicAccess()
    alt Direct access succeeds
        UI->>UI: Set mode = DirectAccess
    else Direct access fails
        UI->>Pref: Read UseShizuku flag
        alt Shizuku preferred
            UI->>INT: IsShizukuAvailable()
            INT-->>UI: Binder availability
            alt Binder ready
                UI->>UI: Set mode = Shizuku
            else Binder absent
                INT->>INT: CheckShizukuPerm(andBind=true)
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
    UI->>Pref: Load cached storage locations & login tokens
    UI->>CM: GetInstalledGameApps(mode, storageLocations)
    CM-->>UI: Installed JP client paths with last-modified metadata
    loop For each detected install
        UI->>CM: GetFileContents(mode, assetstorage.txt)
        CM-->>UI: Base64 assetstorage payload + timestamp
    end
    UI->>REST: GetHandshakeApiResponse(region, assetStorage, device info)
    REST-->>UI: Translation list, bundle status, donor flags
    UI->>UI: Update GUI bindings & schedule, cache metadata
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
        SM->>REST: GetHandshakeApiResponse(region, assetstorage snapshot)
        REST-->>SM: Bundle metadata & file list
        SM->>REST: GetScript(downloadUrl) for each payload
        REST-->>SM: Script bytes
        SM->>SM: Verify checksums & stage file writes
        opt Extra asset updates required
            SM->>REST: SendAssetList(base64 assetstorage, svtIds)
            REST-->>SM: Updated assetstorage blob
        end
        SM->>CM: RemoveFileIfExists(mode, original scripts)
        SM->>CM: WriteFileContents(mode, translated scripts & assetstorage)
        SM-->>UI: ScriptInstallStatus(success, metrics)
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
        UI->>Pref: Load cached manifest & purge extras
        UI->>UI: Enumerate installed bundle file paths
        loop Files to remove
            UI->>CM: RemoveFileIfExists(mode, filePath)
            CM-->>UI: Deletion result
        end
        UI->>Pref: Clear InstalledScript_* and UninstallPurgesExtras_* keys
        UI->>UI: Update status & refresh list
    else User cancels
        UI->>UI: Abort uninstall
    end
```

## Data Location Detection & Permissions
- Direct filesystem mode enumerates each external storage root, walks parent directories, and collects folders whose final segment matches `AppNames.ValidAppNames` (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- SAF mode stores tree URIs collected during onboarding and queries `DocumentFile` children before matching against valid package names; missing permissions trigger prompts via `IntentService` (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`, `RayshiftTranslateFGO.Android/Services/IntentService.cs`).
- Shizuku mode lists directories using NextGenFS bindings exposed by the Android project and requires binder permission checks plus listener setup (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`, `RayshiftTranslateFGO.Android/Services/IntentService.cs`, `RayshiftTranslateFGO.Android/MainActivity.cs`).
- Onboarding pages (`RayshiftTranslateFGO/Views/PreInitializePage.xaml.cs`) prompt the user to choose SAF locations, enable Shizuku if desired, and persist selections for installer use.

## Update & Error Handling
- Asset status flags returned during the handshake (missing, out-of-date, donor-locked) gate installation actions and trigger user-visible warnings before proceeding (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`).
- Installation failures such as permission errors, checksum mismatches, or API failures short-circuit with descriptive error strings propagated back to the UI (`RayshiftTranslateFGO.Android/Services/ScriptManager.cs`).
- `ContentManager` centralizes filesystem error handling for all access modes and surfaces status codes that drive retry prompts or onboarding redirects (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- The README documents user-facing troubleshooting guidance for storage errors (e.g., switching between SAF and Shizuku) and outlines update expectations (`README.md`).
