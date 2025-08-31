import time
import tkinter as tk
from PIL import Image
import pytesseract
import mss
import mss.tools
import json
import os

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


def get_mouse_position(prompt):
    """Get the current mouse position after a countdown using a full-screen overlay."""
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window

    # Create a borderless, transparent, always-on-top window
    overlay = tk.Toplevel(root)
    overlay.attributes("-alpha", 0.3)
    overlay.attributes("-topmost", True)
    overlay.overrideredirect(True)

    # Use mss to get the full virtual screen geometry and make the overlay span all monitors
    with mss.mss() as sct:
        # sct.monitors[0] is the special "all-in-one" monitor bounding box
        virtual_screen = sct.monitors[0]
        overlay.geometry(
            f"{virtual_screen['width']}x{virtual_screen['height']}+{virtual_screen['left']}+{virtual_screen['top']}"
        )

    # Display the prompt on the overlay
    label = tk.Label(overlay, font=("Consolas", 24, "bold"), bg="black", fg="white")
    label.pack(expand=True)

    pos = None
    for i in range(5, 0, -1):
        label.config(text=f"{prompt}\nCapturing in {i}...")
        overlay.update()
        time.sleep(1)

    # Use tkinter's built-in function to get the true global mouse coordinates
    pos = overlay.winfo_pointerxy()

    print(f"Captured: Point(x={pos[0]}, y={pos[1]})")
    overlay.destroy()
    root.destroy()
    return pos


# 1. Get top-left and bottom-right corners
top_left = get_mouse_position("Move mouse to the TOP-LEFT corner of the area")
time.sleep(1)  # Give user time to move the mouse
bottom_right = get_mouse_position("Move mouse to the BOTTOM-RIGHT corner of the area")

# 2. Save coordinates to config.json
x1, y1 = top_left
x2, y2 = bottom_right

config_path = "assets/config.json"
try:
    # Read existing config file
    with open(config_path, "r") as f:
        config_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    # Create new config if it doesn't exist or is invalid
    config_data = {}

# Update the scan_region
config_data["scan_region"] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

# Ensure the assets directory exists
os.makedirs(os.path.dirname(config_path), exist_ok=True)

# Write the updated data back to the file
with open(config_path, "w") as f:
    json.dump(config_data, f, indent=4)

print(f"\n✅ Coordinates saved to {config_path}")
print(f"  Top-Left: (x={x1}, y={y1})")
print(f"  Bottom-Right: (x={x2}, y={y2})")


# 3. Normalize coordinates for screenshot
left = min(x1, x2)
top = min(y1, y2)
width = abs(x2 - x1)
height = abs(y2 - y1)

# Ensure width and height are not zero
if width == 0 or height == 0:
    print(
        "\nError: Invalid region selected (width or height is zero). Please try again."
    )
    exit()

region = {"top": top, "left": left, "width": width, "height": height}

# 4. Take screenshot using mss
with mss.mss() as sct:
    sct_img = sct.grab(region)
    # Convert to a PIL Image
    screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

screenshot.save("selected_region.png")
print("Screenshot saved as selected_region.png")

# 5. OCR
text = pytesseract.image_to_string(screenshot)
print("\n🔍 OCR Result:")
print(text)

# 6. Show OCR result on the correct monitor
root = tk.Tk()
root.title("OCR Result")

# Position the result window near the captured region
root.geometry(f"600x400+{left+50}+{top+50}")

text_box = tk.Text(root, wrap="word", font=("Consolas", 12))
text_box.insert("1.0", text if text.strip() else "[No text detected]")
text_box.pack(expand=True, fill="both")

root.mainloop()
