import uuid
from typing import Dict, Any, List

# Deterministic simulated failure rule catalog based on mobile stress factors
SIMULATION_RULES = [
    {
        "id_prefix": "CRASH_OOM",
        "category": "Application crash",
        "title": "Out of Memory (OOM) Fatal Crash on Image Bitmap Decode",
        "severity": "Critical",
        "trigger": lambda p, c: "1GB" in p.get("ram_category", "") or "2GB" in p.get("ram_category", "") or c.get("memory_pressure") in ["High", "Extreme"],
        "feature": {"id": "catalog_media", "name": "Catalog & Product Media View"},
        "description": "App process terminated with SIGABRT due to java.lang.OutOfMemoryError when decoding uncompressed web banners into memory without downsampling.",
        "expected_behavior": "App should downsample image bitmaps or use WebP thumbnails and LRU memory cache without exceeding 128MB heap limit.",
        "observed_behavior": "Fatal signal 6 (SIGABRT), code -1. Heap exhausted: 192MB allocation failed on budget 2GB device.",
        "suggested_debugging": "Integrate Glide/Coil downsampling with RGB_565 configuration; implement onTrimMemory() to release cached bitmap resources.",
        "confidence": "Deterministic (High)",
        "evidence_type": "Logcat Stacktrace & Memory Dump",
        "evidence_content": "FATAL EXCEPTION: main\njava.lang.OutOfMemoryError: Failed to allocate a 33554448 byte allocation with 4194304 free bytes and 4MB until OOM, max allowed 192MB\n  at android.graphics.BitmapFactory.nativeDecodeStream(Native Method)\n  at com.cheapapp.ui.catalog.MediaAdapter.onBindViewHolder(MediaAdapter.kt:84)\n  at androidx.recyclerview.widget.RecyclerView$Adapter.bindViewHolder(RecyclerView.java:7337)",
        "recipe_steps": [
            "Launch application on a 2GB RAM device profile.",
            "Enable High Memory Pressure via background stress simulator.",
            "Navigate to Catalog Screen and rapidly scroll past 15 high-resolution items.",
            "Observe instantaneous process crash and return to Android launcher."
        ]
    },
    {
        "id_prefix": "NET_TIMEOUT",
        "category": "Network timeout",
        "title": "Checkout Payment Gateway 30s Socket Timeout without Retry",
        "severity": "High",
        "trigger": lambda p, c: c.get("network_condition") in ["Slow connection", "High latency", "Intermittent connectivity"],
        "feature": {"id": "checkout_pay", "name": "Checkout & Payment Processing"},
        "description": "Payment verification request exceeded the 15,000ms socket timeout threshold due to Tier-3 2G/EDGE network latency (RTT > 1800ms).",
        "expected_behavior": "Application should provide an adaptive timeout with exponential backoff and safe idempotency key re-verification.",
        "observed_behavior": "Generic modal error: 'java.net.SocketTimeoutException: failed to connect to api.gateway.in after 15000ms'. User money potentially deducted but order stuck in pending.",
        "suggested_debugging": "Set network timeout to 45s on low-bandwidth networks; store idempotency tokens locally in SQLite before initiating payment requests.",
        "confidence": "High (Simulated 2G/EDGE RTT)",
        "evidence_type": "HTTP Network Telemetry Log",
        "evidence_content": "--> POST https://api.cheapapp.in/v1/checkout/verify (512 bytes)\nRTT: 1840ms | Packet Loss: 22%\n<-- HTTP FAILED: java.net.SocketTimeoutException: timeout\nOkHttp Call Duration: 15004ms. No cached fallback.",
        "recipe_steps": [
            "Set device network preset to 'Slow connection' (simulating 128kbps / 1200ms RTT).",
            "Add item to cart and proceed to UPI / Card payment page.",
            "Tap 'Pay Now' and wait for network verification.",
            "Observe screen hanging for 15 seconds followed by SocketTimeoutException."
        ]
    },
    {
        "id_prefix": "STORAGE_FAIL",
        "category": "Storage write failure",
        "title": "SQLite Disk Full Error on Offline Sync Cache",
        "severity": "High",
        "trigger": lambda p, c: c.get("storage_level") in ["Low (Under 500MB)", "Critical (Under 100MB)"] or "450MB" in p.get("storage", "") or "150MB" in p.get("storage", ""),
        "feature": {"id": "offline_sync", "name": "Offline Order & Cart Persistence"},
        "description": "Failed to persist offline cart cache to Room database when remaining internal storage fell below system threshold (<100MB free).",
        "expected_behavior": "App should check available storage before database write, prune stale analytics logs, and surface a clean 'Low Storage' warning.",
        "observed_behavior": "android.database.sqlite.SQLiteFullException: database or disk is full (code 13 SQLITE_FULL). Data lost upon app restart.",
        "suggested_debugging": "Implement auto-clearing of cached webview images and temporary analytics JSON when StatFs indicates < 200MB free space.",
        "confidence": "High",
        "evidence_type": "Disk I/O Error Logcat",
        "evidence_content": "E/SQLiteDatabase: Error inserting into cart_items: android.database.sqlite.SQLiteFullException: database or disk is full (code 13 SQLITE_FULL)\n  at android.database.sqlite.SQLiteConnection.nativeExecute(Native Method)\n  at com.cheapapp.data.local.CartDao_Impl.insert(CartDao_Impl.java:62)",
        "recipe_steps": [
            "Configure device profile with < 200MB free storage.",
            "Add 3 items to offline shopping list.",
            "Force background sync or app restart.",
            "Items fail to save, showing empty cart with SQLiteFullException logged."
        ]
    },
    {
        "id_prefix": "ANR_UI_BLOCK",
        "category": "Application not responding (ANR)",
        "title": "Main Thread File I/O Causing 5-Second ANR Freeze",
        "severity": "Critical",
        "trigger": lambda p, c: p.get("battery_saver") == "Enabled" or c.get("battery_saver") == "Enabled",
        "feature": {"id": "app_startup", "name": "App Startup & Splash Loading"},
        "description": "During Battery Saver CPU throttling (CPU governor restricted to 800MHz little cores), synchronous SharedPreferences and JSON parsing on the UI thread blocked Looper for 6,200ms.",
        "expected_behavior": "All file I/O and shared preference decryption must occur in background Coroutines/Schedulers, keeping UI thread input response < 16ms.",
        "observed_behavior": "Input dispatching timed out (Waiting to send key event to Window). System dialog displayed: 'CheapApp isn't responding. Close app / Wait'.",
        "suggested_debugging": "Move heavy JSON config hydration off Dispatchers.Main onto Dispatchers.IO; replace SharedPreferences with DataStore async.",
        "confidence": "Deterministic (High)",
        "evidence_type": "ANR traces.txt extract",
        "evidence_content": "\"main\" prio=5 tid=1 Blocked\n  | sysTid=18492 nice=-10 cpm=15% sched=0/0 handle=0x7bb8f1a\n  at java.io.FileInputStream.readBytes(Native Method)\n  at com.cheapapp.util.ConfigLoader.loadLocalCatalogSync(ConfigLoader.kt:42)\n  at com.cheapapp.MainActivity.onCreate(MainActivity.kt:55)",
        "recipe_steps": [
            "Enable Battery Saver on 2GB budget profile.",
            "Kill app process completely.",
            "Tap app icon to trigger cold startup.",
            "Tap screen repeatedly within first 3 seconds; observe OS ANR dialog."
        ]
    },
    {
        "id_prefix": "STATE_LOSS",
        "category": "Lost application state after process interruption",
        "title": "Form Input Eviction During Incoming Call Process Death",
        "severity": "Medium",
        "trigger": lambda p, c: c.get("background_interruption") == "Aggressive (Low RAM Kill)" or "Go Edition" in p.get("android_version", ""),
        "feature": {"id": "kyc_form", "name": "User Registration & KYC Form"},
        "description": "When an incoming phone call or background SMS task triggered Android Go's Low Memory Killer, Activity was destroyed without saving bundle state.",
        "expected_behavior": "Activity should persist partial form state into SavedStateHandle or ViewModel SavedStateRegistryProvider.",
        "observed_behavior": "Returning to app after call showed blank form. User had to re-enter 14 KYC fields and re-capture ID proof.",
        "suggested_debugging": "Implement onSaveInstanceState() or Compose rememberSaveable() for form text fields and multi-step stepper state.",
        "confidence": "High",
        "evidence_type": "Lifecycle Transition Log",
        "evidence_content": "ActivityManager: Killing 21094:com.cheapapp/u0a142 (adj 906): lowmem (free 22MB)\nActivityRecord: Resuming com.cheapapp/.ui.kyc.KycActivity without savedInstanceState\nW/KycActivity: savedInstanceState is NULL. Resetting step index to 0.",
        "recipe_steps": [
            "Open User KYC form and fill in Name, Aadhaar number, and Address.",
            "Simulate incoming call / background switch (trigger background process kill).",
            "Return to application from recent apps tray.",
            "Notice all completed fields are wiped and reset to blank."
        ]
    },
    {
        "id_prefix": "DUP_SUBMIT",
        "category": "Duplicate form submission",
        "title": "Double Order Placement Due to Lagging Button Debounce",
        "severity": "Medium",
        "trigger": lambda p, c: c.get("network_condition") in ["Slow connection", "High latency"] and ("1GB" in p.get("ram_category", "") or "2GB" in p.get("ram_category", "")),
        "feature": {"id": "order_submit", "name": "Order Submission & Booking"},
        "description": "Under high CPU load and slow network, the 'Place Order' button did not disable immediately upon click. Impatient user double-tapped, resulting in two duplicate orders.",
        "expected_behavior": "Disable CTA button immediately upon first click event and attach client-generated UUID idempotency key to payload.",
        "observed_behavior": "Two distinct order records (#IN-94021 and #IN-94022) created on server 450ms apart for identical cart contents.",
        "suggested_debugging": "Use single-click debounce listener (min 1500ms delay); disable view hierarchy clickability synchronously.",
        "confidence": "High",
        "evidence_type": "Server API Access Log",
        "evidence_content": "POST /api/v1/orders 200 OK (ReqID: 94021, Time: 11:42:01.200, IP: 106.195.x.x)\nPOST /api/v1/orders 200 OK (ReqID: 94022, Time: 11:42:01.650, IP: 106.195.x.x) DUPLICATE_PAYLOAD",
        "recipe_steps": [
            "Set network to High Latency (1500ms).",
            "Fill order details on a budget device with heavy UI frame drops.",
            "Tap 'Confirm Order' button twice in rapid succession.",
            "Inspect backend database; observe two orders created with separate billing charges."
        ]
    },
    {
        "id_prefix": "UNRESPONSIVE_UI",
        "category": "Unresponsive UI",
        "title": "RecyclerView Jitter & 14 dropped frames during catalog scroll",
        "severity": "Low",
        "trigger": lambda p, c: "Go" in p.get("android_version", "") or "1GB" in p.get("ram_category", ""),
        "feature": {"id": "catalog_scroll", "name": "Item Catalog List"},
        "description": "Skipped 14 frames on Choreographer; UI thread overloaded doing layout inflation inside onBindViewHolder.",
        "expected_behavior": "Maintain smooth 60fps / 16ms render loop with view recycling and pre-inflated view pools.",
        "observed_behavior": "Visible stutter and delayed touch-drag response during scrolling.",
        "suggested_debugging": "Flatten XML hierarchy; eliminate nested LinearLayouts; implement ViewBinding without reflection.",
        "confidence": "High",
        "evidence_type": "Choreographer Frame Log",
        "evidence_content": "I/Choreographer: Skipped 14 frames! The application may be doing too much work on its main thread.\nTotal jank frame count: 38 (42% of total frames during 5s scroll window).",
        "recipe_steps": [
            "Select 1GB GraminTab profile.",
            "Scroll rapidly through product catalogue.",
            "Observe screen tearing, jerky movement, and missed swipe gestures."
        ]
    }
]

def generate_simulated_failures(device_profile: Dict[str, Any], conditions: Dict[str, Any], test_run_id: str) -> List[Dict[str, Any]]:
    """
    Evaluates rule triggers against selected device and environmental stress factors.
    Returns deterministic, reproducible failure records.
    """
    failures = []
    
    for rule in SIMULATION_RULES:
        if rule["trigger"](device_profile, conditions):
            f_id = f"{rule['id_prefix']}_{str(uuid.uuid4())[:8]}"
            failures.append({
                "id": f_id,
                "title": rule["title"],
                "description": rule["description"],
                "category": rule["category"],
                "severity": rule["severity"],
                "confidence": rule["confidence"],
                "mode": "simulation",
                "expected_behavior": rule["expected_behavior"],
                "observed_behavior": rule["observed_behavior"],
                "suggested_debugging": rule["suggested_debugging"],
                "feature": rule["feature"],
                "test_run_id": test_run_id,
                "device_profile": device_profile,
                "conditions": conditions,
                "evidence": [
                    {
                        "id": f"ev_{f_id}_1",
                        "type": rule["evidence_type"],
                        "content": rule["evidence_content"],
                        "timestamp": "2026-10-19 11:45:00"
                    }
                ],
                "reproduction_recipe": {
                    "id": f"rec_{f_id}",
                    "preconditions": f"Device Profile: {device_profile.get('name')}. Android: {device_profile.get('android_version')}.",
                    "device_config": f"RAM: {device_profile.get('ram_category')}, Battery Saver: {conditions.get('battery_saver', 'Default')}",
                    "network_storage": f"Network: {conditions.get('network_condition')}, Storage Free: {conditions.get('storage_level')}",
                    "steps": rule["recipe_steps"],
                    "expected": rule["expected_behavior"],
                    "observed": rule["observed_behavior"],
                    "debug_direction": rule["suggested_debugging"]
                }
            })

    return failures
