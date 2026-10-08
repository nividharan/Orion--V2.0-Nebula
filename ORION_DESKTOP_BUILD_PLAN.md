# 🖥️ Orion Desktop Controller: Dedicated Building Plan
## Architecture: Universal Multi-Model Substrate (Nebula Web + Blender 3D + Desktop Apps)

---

## 1. System Identity & Mission

**Orion** is the **Universal Operating System & Desktop Automation Substrate**. 
It is explicitly designed to be **model-agnostic**:
* Orion does **not** hardcode itself to Chrome or Nebula.
* Orion acts as the unified low-level OS driver that powers **multiple specialized cognitive models**:
  1. **Model 1: Nebula** ➔ Specialized Cognitive Agent for Google Chrome & Web operations.
  2. **Model 2: Blender Model** ➔ Specialized Cognitive Agent for Blender 3D (3D modeling, viewports, rendering, `bpy` scripts).
  3. **Future Models** ➔ Any native Windows desktop workflow (Photoshop, VS Code, Unreal Engine).

```
┌────────────────────────────────────────────────────────────────────────┐
│               AUTOGEN MULTI-AGENT COGNITIVE SOCIETY                     │
│               (High-Level Task Planning & Dispatcher)                  │
└───────────────┬────────────────────────┬───────────────────────────────┘
                │                        │
       [Web Tasks]                       │ [3D / Modeling Tasks]
                ▼                        ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│     NEBULA MODEL             │  │     BLENDER MODEL            │
│   (Chrome & Web Engine)      │  │   (3D Ops, bpy, Viewports)   │
└───────────────┬──────────────┘  └──────────────┬───────────────┘
                │                                │
                ▼                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ORION UNIVERSAL DESKTOP SUBSTRATE                    │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ App Adapter Layer: [ChromeAdapter] [BlenderAdapter] [WinAdapter]│  │
│   └────────────────────────────────────────────────────────────────┘   │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Native OS Controls: SendInput Typing · Bezier Mouse · Windows  │   │
│   │ Process Manager · Multi-Monitor GDI Screen Capture · #32770    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture & File Inventory

Orion is organized into a clean, extensible package: `orion_desktop/`:

```
Orion Universal Desktop Substrate/
├── orion_desktop/
│   ├── __init__.py               # Exports OrionSubstrate and Adapter handles
│   ├── substrate.py              # Central OrionSubstrate manager & dispatch
│   ├── adapters/                 # Pluggable Application Adapters
│   │   ├── base.py               # Abstract BaseAppAdapter interface
│   │   ├── generic.py            # Generic Windows Application Adapter (Notepad, Explorer)
│   │   ├── chrome.py             # Chrome Window & Process Adapter (used by Nebula)
│   │   └── blender.py            # Blender Window, Process & Hotkey Adapter (for Blender Model)
│   ├── controls/                 # Hardware-Level OS Controls
│   │   ├── keyboard.py           # Win32 SendInput keyboard, virtual keys, chords, cadence
│   │   ├── mouse.py              # Cubic Bezier trajectories, smooth clicks, drag-and-drop
│   │   ├── window_manager.py     # EnumWindows, AttachThreadInput focus, positioning
│   │   ├── process_manager.py    # Process launch (blender.exe, chrome.exe), PID watchdog
│   │   ├── screen_capture.py     # GDI/Pillow multi-monitor & window-viewport capture
│   │   └── dialog_detector.py    # System #32770 dialogs & crash alerts
├── desktop_controller.py         # Orion OS layer unified CLI & programmatic facade
└── tests/
    └── test_orion_desktop.py     # Unit tests with mocked Win32 ctypes
```

---

## 3. The App Adapter Pattern (Why This Makes Blender Seamless)

To allow the upcoming **Blender Model** to plug into Orion just as easily as Nebula, Orion uses an **Abstract App Adapter**:

### `BaseAppAdapter` Interface (`orion_desktop/adapters/base.py`)
```python
class BaseAppAdapter(ABC):
    """Base interface implemented for each target application ecosystem."""
    
    @property
    @abstractmethod
    def app_name(self) -> str: ...
    
    @abstractmethod
    def launch(self, *args, **kwargs) -> int:
        """Launches target process, returns PID."""
        ...
        
    @abstractmethod
    def find_window(self) -> Optional[int]:
        """Finds main application HWND by title/class."""
        ...
        
    @abstractmethod
    def focus(self) -> bool:
        """Safely brings application to active foreground."""
        ...
        
    @abstractmethod
    def capture_viewport(self) -> Optional[bytes]:
        """Captures active application viewport for visual verification."""
        ...
```

---

### Specializing for Blender (`orion_desktop/adapters/blender.py`)

Blender requires specific OS-level interactions that differ from web browsers:
1. **Window Identification**:
   * Class: `GHOST_WindowClass` (Blender's custom OpenGL/Vulkan window class).
   * Title matcher: Matches `Blender [version] - [file.blend]`.
2. **Process Lifecycle**:
   * Locates `blender.exe` via default paths (`C:\Program Files\Blender Foundation\Blender *\blender.exe`) or `PATH`.
   * Supports launching with `--python-expr` or `--python-console` background sockets.
3. **Blender-Specific Shortcut Chording**:
   * Hotkey macros supported natively by Orion's keyboard engine:
     * `Shift+A` (Add Menu: Mesh, Light, Camera).
     * `G` (Grab/Move), `R` (Rotate), `S` (Scale) + axis locks (`X`, `Y`, `Z`).
     * `Numpad 1 / 3 / 7` (Front, Side, Top viewports).
     * `Tab` (Toggle Object / Edit Mode).
     * `F12` (Trigger Render) and `Ctrl+F12` (Render Animation).
     * `Z` (Viewport Shading Pie Menu: Wireframe, Solid, Rendered).
4. **Viewport Visual Inspection**:
   * Crops the 3D Viewport rect specifically for the Screen Watcher and Gemini Multimodal Vision to evaluate 3D geometry and shading.

---

## 4. Hardware-Level Subsystem Specifications

### Subsystem 1: Hardware-Level Keyboard (`controls/keyboard.py`)
* Uses Win32 `SendInput` with `INPUT_KEYBOARD` structs.
* Virtual Key Code (`VK_*`) translation supporting:
  * Standard typing: ASCII and Unicode text.
  * Blender & Chrome chords: `Shift+A`, `Ctrl+Z`, `Alt+Tab`, `Win+R`, `Ctrl+S`.
  * Special keys: `Numpad0`–`Numpad9`, `F1`–`F12`, `Esc`, `Tab`, `Spacebar`.
* Human Cadence Engine: Configurable Gaussian variance ($50\text{ ms} \pm 15\text{ ms}$) or instant macro execution for hotkeys.

### Subsystem 2: Natural Mouse Trajectories (`controls/mouse.py`)
* Cubic Bezier Curves ($P_0 \to P_1 \to P_2 \to P_3$) with randomized control points.
* Specialized mouse actions for 3D Viewports:
  * `middle_click_drag(dx, dy)` (Rotate 3D Viewport in Blender).
  * `shift_middle_click_drag(dx, dy)` (Pan 3D Viewport in Blender).
  * `wheel_zoom(delta)` (Zoom in/out).
  * `left_click(x, y)` and `right_click(x, y)`.

### Subsystem 3: Window Focus & Placement (`controls/window_manager.py`)
* Enumerates top-level application windows.
* Uses `AttachThreadInput` to bypass Windows foreground lock restrictions when switching between Chrome, Blender, and terminal.
* Geometries: `minimize`, `maximize`, `restore`, `dock_left`, `dock_right`.

### Subsystem 4: Process Watchdog (`controls/process_manager.py`)
* Spawns non-blocking subprocesses with PID tracking.
* Monitors process health, CPU/RAM utilization, and unresponsive states.
* Graceful termination via `WM_CLOSE` before `SIGKILL`.

### Subsystem 5: Multi-Monitor Screen Capture (`controls/screen_capture.py`)
* Fast GDI capture of virtual multi-monitor screens.
* Window-specific viewport cropping (e.g. Blender 3D Viewport or Chrome page rect) for Gemini Vision inspection.

---

## 5. Phased Implementation Roadmap for Orion

| Step | Action | Output / File | Verification Method |
|:---:|---|---|---|
| **O.1** | Create `orion_desktop/` & `BaseAppAdapter` interface | `orion_desktop/substrate.py`<br>`orion_desktop/adapters/base.py` | Unit tests verifying adapter registration |
| **O.2** | Implement Win32 Keyboard & Mouse engine | `orion_desktop/controls/keyboard.py`<br>`orion_desktop/controls/mouse.py` | Verify Bezier curve generation & chord mapping |
| **O.3** | Implement Window Manager & Process Watchdog | `orion_desktop/controls/window_manager.py`<br>`orion_desktop/controls/process_manager.py` | Mock Win32 `EnumWindows` and process tracking |
| **O.4** | Implement ChromeAdapter (for Nebula) & BlenderAdapter (for Blender Model) | `orion_desktop/adapters/chrome.py`<br>`orion_desktop/adapters/blender.py` | Test window class detection & hotkey chording |
| **O.5** | Screen Capture & System Dialog Detector | `orion_desktop/controls/screen_capture.py`<br>`orion_desktop/controls/dialog_detector.py` | Verify viewport cropping & `#32770` dialog signal |
| **O.6** | Expose multi-app commands in `desktop_controller.py` CLI | [`desktop_controller.py`](file:///c:/skill/desktop_controller.py) | CLI commands: `orion focus blender`, `orion hotkey "shift+a"` |
| **O.7** | Offline Test Suite for Orion Substrate | `tests/test_orion_desktop.py` | 100% passing tests (zero external dependencies) |

---

## 6. How the Blender Model Plugs into Orion in the Future

When you build the **Blender Model**, it will simply import Orion's substrate:

```python
from orion_desktop import OrionSubstrate

orion = OrionSubstrate.get_adapter("blender")

# 1. Launch & focus Blender
orion.launch_or_focus()

# 2. Blender Model plans 3D actions, Orion executes native inputs:
orion.hotkey("shift+a")           # Open Add Menu
orion.type("Cube")               # Search primitive
orion.press("enter")             # Add Cube
orion.hotkey("s")                # Scale mode
orion.type("2")                  # Scale factor 2x
orion.press("enter")             # Confirm scale
orion.hotkey("f12")              # Trigger Render

# 3. Screen Watcher + Gemini Vision inspects the Render window!
```

This guarantees that Orion is **100% reusable, extensible, and ready for both Nebula (Web) and your upcoming Blender Model (3D)** without requiring any architectural rewrites!
