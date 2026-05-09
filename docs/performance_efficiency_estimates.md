# Performance and Efficiency Estimates

These estimates are planning targets for the Linux Pop!_OS COSMIC GTK app first,
then the public GTK `.deb`, Tauri Linux `.deb`/AppImage, Windows, and macOS
builds. Treat numbers here as estimates until replaced by measured results.

## Baseline Context

- Machine: ASRock X600 Deskmeet profile from `/home/erich/X600 Deskmeet.md`.
- CPU: AMD Ryzen 7 9700X, 8 cores / 16 threads.
- Memory: 64 GB DDR5.
- Storage: fast NVMe system/app storage.
- GPU/display: RTX 4060 Ti 16 GB driving a 3440 x 1440 high-refresh OLED.
- Current local data shape during planning: 215 owned releases, 17 wantlist entries,
  251 cached covers using about 26 MB on disk.
- Local query timings during planning: owned browse without cover preload about
  6 ms, wantlist about 1.5 ms, collection summary about 0.8 ms, value dashboard
  about 5 ms. The main risk is UI/image work, not SQLite query latency.

## Estimated Impact

| Change | Current Risk | Expected CPU Impact | Expected Memory Impact | Expected GPU Impact | How To Validate |
| --- | --- | --- | --- | --- | --- |
| Shared performance profile and worker caps | Independent 32-worker cover pools can create startup bursts | 50-80% lower peak cover-prefetch CPU/thread pressure during startup | Lower thread stack/queue overhead | Fewer bursty texture uploads after startup | `--perf-report`, thread count, `ps` CPU sampling |
| Process-wide image fetch deduplication | Carousel, browse preload, and cache warm can fetch the same URL concurrently | Avoids duplicate network/decode/write work for shared URLs | Reduces duplicate response buffers | Indirect; fewer repeated decodes/uploads | Concurrent image-cache unit test and cache fetch counters |
| Default visible/nearby cover preload | App can block initial render while warming every cover | Faster first paint; less startup fan spike | Fewer queued image results retained at once | Less upload pressure during initial layout | Compare `--cover-preload visible` vs `all` smoke timings |
| Carousel inflight cap and smaller lookahead | Spin can queue far more covers than the user will see soon | 40-70% lower carousel background CPU on quick navigation | Smaller executor backlog | Fewer stale texture uploads | Carousel prefetch cap tests and real spin sampling |
| Carousel texture LRU | Decoded textures can grow without a fixed cap | Neutral to slightly lower CPU after warm cache; prevents late eviction storms | Caps decoded cover memory; expected stable RSS after long browsing | Caps GPU texture memory growth and upload churn | Long carousel browse with RSS/thread/GPU observation |
| Lazy gallery chunking | Gallery creates a GTK card for every release at once | 60-90% lower first gallery render work for large collections | Fewer live GTK widgets before scrolling | Fewer image placeholders/textures allocated at once | 1,000-item fixture widget-population test |
| Async/lazy detail enrichment | Selection can perform cache/DB detail work on navigation path | Less UI-thread jank; total CPU roughly unchanged | No major change | No major change | Gallery/carousel selection responsiveness checks |
| Deferred inactive view population | Browse load populates text, carousel, and gallery surfaces together | 30-60% less startup main-thread GTK work on large collections | Fewer widgets until needed | Fewer non-visible image widgets/textures | Startup report plus tab-switch smoke |
| Game idle suspension | Unfocused app can retain queued prefetch, decoded textures, or animation timers | Near-zero idle CPU after first load; target <=0.5 CPU-seconds over 120s probe | Stable RSS; trims decoded carousel texture cache after background delay | Prevents app-driven texture upload churn while a game owns the GPU | `./scripts/gui_idle_probe.sh 120`, `ps`, optional `nvidia-smi` |
| Lazy Value dashboard | Browse startup computes value dashboard and hidden gems before the Value tab is used | Removes a parallel dashboard query group from normal Browse launch | Less dashboard/list data retained until needed | No direct GPU impact | Value-tab smoke and dashboard refresh tests |
| Tauri request cancellation | Rapid filters can let stale API responses update UI | Modest CPU reduction, better correctness under quick typing | Less retained stale response data | Not applicable | Playwright stale-response and abort tests |

## Measured Results

Record implementation results here after each validation run.

| Date | Build/App | Scenario | CPU | Memory | GPU | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-05-01 | Headless GTK smoke | 215-item balanced startup smoke | user 0.423s, system 0.042s | max RSS 218,552 KB | not measured under xvfb | `--perf-report --smoke-test --limit 215`; 4 cover workers, 8 carousel inflight, 72 initial gallery items |
| 2026-05-01 | Headless GTK smoke | 20-item full cover preload smoke | user 0.489s, system 0.041s | max RSS 238,400 KB | not measured under xvfb | `--perf-report --cover-preload all --smoke-test --limit 20`; 20 cached covers |
| 2026-05-01 | Headless GTK idle probe | 10s game-profile forced background suspension | idle delta: user 1.2797s, system 0.1252s | max RSS 232,800 KB | not measured under xvfb | `./scripts/gui_idle_probe.sh 10`; all prefetch, animation, resize, and gallery append state inactive. Headless Xvfb/software rendering overstates COSMIC occluded-window CPU. |
| TBD | Local GTK/COSMIC | 60s idle after launch | TBD | TBD | TBD | Run from installed desktop launcher |
| TBD | Local GTK/COSMIC | Carousel quick navigation | TBD | TBD | TBD | Check thread count and fan/CPU behavior |
| TBD | Local GTK/COSMIC | Gallery scroll/select | TBD | TBD | TBD | Confirm lazy append and detail pane |
| TBD | Public Tauri build | Rapid collection filters | TBD | TBD | n/a | Confirm request cancellation |

## Validation Commands

```bash
dplayer-gui --perf-report --smoke-test --limit 215
dplayer-gui --perf-report --cover-preload all --smoke-test --limit 215
DP_PERF_PROFILE=game ./scripts/gui_idle_probe.sh 120
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
venv/bin/python -m pytest -q --durations=20
npm --prefix webapp run build
npm --prefix webapp run test:e2e
```

For the real COSMIC desktop session, sample the installed process for 60 seconds
after the app reaches idle. Record average CPU, max RSS, thread count, and any
visible GPU/fan behavior in the measured-results table.
