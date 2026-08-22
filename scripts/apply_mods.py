#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_mods.py <firmware-root>")

root = Path(sys.argv[1]).resolve()
board = root / "main" / "boards" / "waveshare-s3-rlcd-4.2"
custom = board / "custom_lcd_display.cc"
data = board / "data_update_task.cc"

if not custom.exists() or not data.exists():
    raise SystemExit(f"board source not found under: {board}")

# ---------------------------------------------------------------------------
# 1) AI long replies: RLCD-friendly behavior
#    Original firmware animates the label one pixel at a time, then repeats
#    forever. That causes lots of full RLCD refreshes and makes a long answer
#    feel very slow. We replace it with a static "latest visible page" view.
# ---------------------------------------------------------------------------
text = custom.read_text(encoding="utf-8")
start_marker = "void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {"
end_marker = "void CustomLcdDisplay::SetEmotion(const char* emotion) {"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate SetChatMessage/SetEmotion in custom_lcd_display.cc")

new_func = r'''void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {
    DisplayLockGuard lock(this);
    if (chat_status_label_ == nullptr && music_chat_status_label_ == nullptr) return;
    if (!content || strlen(content) == 0) return;

    // RLCD optimisation: never run the old per-pixel infinite scroll animation.
    // A reflective 1-bit panel is much happier with occasional static refreshes.
    if (chat_status_label_) {
        lv_anim_delete(chat_status_label_, nullptr);
    }

    SetShowingSystemInfo(false);

    if (chat_status_label_) {
        lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(chat_status_label_, content);

        // Our Xingyu dialog uses the complete 126 px text width, so there is no
        // old 84 px emoji offset. Start from the top-left for short messages.
        lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        lv_obj_update_layout(chat_status_label_);

        int label_h = lv_obj_get_height(chat_status_label_);
        lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
        int visible_h = parent ? lv_obj_get_content_height(parent) : 134;

        if (label_h > visible_h) {
            // Long / streaming answer: immediately show the newest visible page.
            // No pixel animation, no 1.5 s delay and no infinite restart.
            lv_obj_set_y(chat_status_label_, visible_h - label_h);
            ESP_LOGI(TAG, "AI answer long (%dpx > %dpx): show latest page without scrolling",
                     label_h, visible_h);
        }
    }

    // Keep the other pages in sync with the same AI text.
    if (music_chat_status_label_) {
        lv_label_set_long_mode(music_chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(music_chat_status_label_, content);
    }
    if (pomo_chat_status_label_) {
        lv_label_set_long_mode(pomo_chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(pomo_chat_status_label_, content);
    }
}
'''
text = text[:start] + new_func + text[end:]
custom.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Background status text must also use the new dialog's full width.
# 3) Weather card is narrow in the new layout, so omit city to avoid clipping.
# ---------------------------------------------------------------------------
dtext = data.read_text(encoding="utf-8")
old_align = "lv_obj_align(self->chat_status_label_, LV_ALIGN_LEFT_MID, 64 + 20, 0);"
if old_align in dtext:
    dtext = dtext.replace(
        old_align,
        "lv_obj_align(self->chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);"
    )
else:
    print("warning: old chat alignment line was not found; continuing")

weather_re = re.compile(
    r'snprintf\(weather_buf, sizeof\(weather_buf\), "%s %s %s°C",\s*\n\s*wd\.city\.c_str\(\), wd\.text\.c_str\(\), wd\.temp\.c_str\(\)\);'
)
dtext, count = weather_re.subn(
    'snprintf(weather_buf, sizeof(weather_buf), "%s %s°C",\n                 wd.text.c_str(), wd.temp.c_str());',
    dtext,
    count=1,
)
if count == 0:
    print("warning: weather text format was not found; continuing")

data.write_text(dtext, encoding="utf-8")

print("Xingyu RLCD modifications applied successfully")
