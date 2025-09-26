# TranslateFGO Installer Mechanics Recon

## License Attribution
- The repository distributes the application under the MIT License and requires retention of the copyright notice and permission statement in derivative works (`LICENCE.txt`).
- The README reiterates the MIT licensing for the installer code and clarifies that bundle creation, translation, and API services remain private while the public app only handles installation (`README.md`).

## Code Location Map
| Concern | Primary Files |
| --- | --- |
| Installer UI orchestration, handshake workflow, and bundle status rendering | `RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`
| Filesystem access for Direct, SAF, and Shizuku modes plus game discovery helpers | `RayshiftTranslateFGO.Android/Services/ContentManager.cs`
| Script download, checksum verification, assetstorage maintenance, and file writes | `RayshiftTranslateFGO.Android/Services/ScriptManager.cs`
| REST client used for handshake metadata, file downloads, telemetry, and asset list refresh | `RayshiftTranslateFGO/Services/RestfulAPI.cs`
| SAF/Shizuku permission prompts, binder binding, and system intent helpers | `RayshiftTranslateFGO.Android/Services/IntentService.cs`
| Shizuku NextGenFS bindings for privileged filesystem operations | `RayshiftTranslateFGO.NextGenFS/Additions/NextGenFS.cs`
| Onboarding that captures SAF tree URIs, Shizuku opt-in, and caches storage metadata | `RayshiftTranslateFGO/Views/PreInitializePage.xaml.cs`
| Background auto-update worker that reuses install routines | `RayshiftTranslateFGO.Android/RayshiftTranslationUpdateWorker.cs`
| Valid JP client identifiers used during storage scanning | `RayshiftTranslateFGO/Util/AppNames.cs`

## Data Location Detection & Permissions
- During onboarding, the pre-initialization flow triggers SAF tree pickers or Shizuku permission requests, then persists selected document URIs and flags via `Preferences` for later use (`RayshiftTranslateFGO/Views/PreInitializePage.xaml.cs`, `RayshiftTranslateFGO.Android/Services/IntentService.cs`).
- When the installer view refreshes, it reloads cached storage URIs and Shizuku toggles from `Preferences`, clears cached directory metadata, and determines the active filesystem mode by probing direct access first and falling back to user-selected Shizuku or SAF modes (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`, `RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- Game discovery enumerates each accessible root depending on the mode: direct filesystem scanning walks `Android/data` subdirectories, SAF mode queries `DocumentFile` children, and Shizuku mode lists directories through NextGenFS binder calls; each candidate is validated against the known JP package list before being recorded as an install target (`RayshiftTranslateFGO.Android/Services/ContentManager.cs`, `RayshiftTranslateFGO/Util/AppNames.cs`).
- Asset availability checks fetch `assetstorage.txt` via the selected mode and capture timestamps to choose the freshest install path; permission failures trigger onboarding redirects or Shizuku setup messaging within the installer view (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`, `RayshiftTranslateFGO.Android/Services/ContentManager.cs`).

## Sequence Diagrams

### Filesystem Mode Selection
```mermaid
sequenceDiagram
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    participant INT as IntentService.cs
    UI->>Pref: Load SAF tree URIs & Shizuku toggle
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
        REST-->>SM: Bundle metadata & donor flags
        SM->>REST: GetScript(downloadUrl) for each asset
        REST-->>SM: Script bytes
        SM->>SM: Verify hashes, stage writes, prep assetstorage updates
        opt Extra-stage assets required
            SM->>REST: SendAssetList(base64 assetstorage, svtIds)
            REST-->>SM: Updated assetstorage blob
        end
        SM->>CM: RemoveFileIfExists(mode, original files)
        SM->>CM: WriteFileContents(mode, translated payloads)
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
        UI->>Pref: Load InstalledScript_* manifest & extras
        UI->>UI: Enumerate bundle file list (scripts + extras)
        loop Files to remove
            UI->>CM: RemoveFileIfExists(mode, path)
            CM-->>UI: Deletion status
        end
        UI->>Pref: Clear InstalledScript_* and UninstallPurgesExtras_* keys
        UI->>UI: Update status and refresh list
    else User cancels
        UI->>UI: Abort uninstall
    end
```

### Update Flow
```mermaid
sequenceDiagram
    participant UI as InstallerPage.xaml.cs
    participant Pref as Xamarin.Essentials.Preferences
    participant CM as ContentManager.cs
    participant REST as RestfulAPI.cs
    UI->>Pref: Load storage URIs, login tokens, installed bundle cache
    UI->>CM: GetInstalledGameApps(mode, storageLocations)
    CM-->>UI: JP client paths + timestamps
    loop Each detected install
        UI->>CM: GetFileContents(mode, assetstorage.txt)
        CM-->>UI: Base64 assetstorage + last modified
    end
    UI->>REST: GetHandshakeApiResponse(region, assetstorage)
    REST-->>UI: Translation groups, status flags, announcements
    UI->>UI: Update GUI, release schedule, donor state, cached metadata
```

## Update & Error Handling
- The installer surfaces handshake asset status warnings (missing, update required, time-traveler, corrupt) before allowing installs, matching the README guidance on keeping the game patched (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`, `README.md`).
- Automatic updates reuse the script manager to reinstall the last known bundle when background workers trigger, falling back to telemetry logging if failures occur (`RayshiftTranslateFGO.Android/RayshiftTranslationUpdateWorker.cs`).
- Permissions or checksum failures raise descriptive alerts, optionally redirecting users back to storage setup or Shizuku onboarding when `ContentManager` encounters blocked paths (`RayshiftTranslateFGO/Views/InstallerPage.xaml.cs`, `RayshiftTranslateFGO.Android/Services/ContentManager.cs`).
- User-facing troubleshooting advice encourages switching filesystem modes (SAF vs Shizuku), reinstalling, or verifying connectivity, aligning with the README’s support section (`README.md`).
