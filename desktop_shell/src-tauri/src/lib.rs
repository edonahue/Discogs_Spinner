use std::{sync::Mutex, thread, time::Duration};

use tauri::{AppHandle, Manager, WindowEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use tauri_plugin_updater::UpdaterExt;

// ---------------------------------------------------------------------------
// Sidecar state
// ---------------------------------------------------------------------------

struct SidecarState(Mutex<Option<CommandChild>>);

// ---------------------------------------------------------------------------
// Health-check constants
// ---------------------------------------------------------------------------

const HEALTHZ_URL: &str = "http://127.0.0.1:8768/healthz";
/// How long to wait between polls (ms).
const POLL_INTERVAL_MS: u64 = 500;
/// Maximum number of poll attempts before giving up (~15 s).
const POLL_MAX_ATTEMPTS: u32 = 30;

// ---------------------------------------------------------------------------
// Health-check helper
// ---------------------------------------------------------------------------

/// Block (in a background thread) until the API sidecar responds OK or we time out.
fn wait_for_api() -> bool {
    for attempt in 1..=POLL_MAX_ATTEMPTS {
        match ureq::get(HEALTHZ_URL).call() {
            Ok(resp) if resp.status() == 200 => {
                eprintln!("[discogs-spinner] API ready after {} poll(s)", attempt);
                return true;
            }
            _ => {}
        }
        thread::sleep(Duration::from_millis(POLL_INTERVAL_MS));
    }
    eprintln!("[discogs-spinner] API did not respond within the timeout period");
    false
}

// ---------------------------------------------------------------------------
// Sidecar lifecycle
// ---------------------------------------------------------------------------

fn spawn_sidecar(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let sidecar_cmd = app.shell().sidecar("dplayer-api")?;

    // Forward relevant env vars so the sidecar can locate the DB and token.
    // XDG vars and DISCOGS_TOKEN are inherited from the parent process
    // automatically; this explicit pass-through makes the intent visible.
    let sidecar_cmd = sidecar_cmd.env(
            "DISCOGS_API_HOST",
            std::env::var("DISCOGS_API_HOST").unwrap_or_default(),
        );

    let (_rx, child) = sidecar_cmd.spawn()?;
    *app.state::<SidecarState>().0.lock().unwrap() = Some(child);
    Ok(())
}

fn kill_sidecar(app_handle: &AppHandle) {
    if let Some(child) = app_handle
        .state::<SidecarState>()
        .0
        .lock()
        .unwrap()
        .take()
    {
        let _ = child.kill();
        eprintln!("[discogs-spinner] API sidecar stopped");
    }
}

// ---------------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------------

/// Check for an available update and return the new version string, or None.
/// Called from the React frontend via invoke('check_update').
#[tauri::command]
async fn check_update(app: AppHandle) -> Option<String> {
    match app.updater() {
        Ok(updater) => match updater.check().await {
            Ok(Some(update)) => Some(update.version.clone()),
            _ => None,
        },
        Err(_) => None,
    }
}

// ---------------------------------------------------------------------------
// App entry point
// ---------------------------------------------------------------------------

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(SidecarState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![check_update])
        .setup(|app| {
            spawn_sidecar(app)?;

            // Poll healthz in the background; log if the sidecar is slow.
            // The webview loads `frontendDist` immediately — the React app itself
            // shows a loading state until the API responds.
            thread::spawn(|| {
                wait_for_api();
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                kill_sidecar(window.app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Discogs Spinner");
}
