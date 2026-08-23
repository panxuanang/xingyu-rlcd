#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_mods.py <firmware-root>")

root = Path(sys.argv[1]).resolve()
board = root / "main" / "boards" / "waveshare-s3-rlcd-4.2"
custom = board / "custom_lcd_display.cc"
header = board / "custom_lcd_display.h"
data = board / "data_update_task.cc"
weather = board / "weather_ui.cc"

for path in (custom, header, data, weather):
    if not path.exists():
        raise SystemExit(f"required source not found: {path}")

# ---------------------------------------------------------------------------
# V4 philosophy:
# - Keep the enlarged Xingyu chat layout.
# - Restore the author's original message path: every sentence_start replaces
#   the text immediately. NO accumulation, NO fake streaming, NO application.cc
#   changes, NO LVGL priority/timer changes.
# - If one incoming sentence is taller than the enlarged box, scroll it once.
# ---------------------------------------------------------------------------

# 1) Header: only UI handles + expanded-state flag. No stream buffer.
htext = header.read_text(encoding="utf-8")
if "lv_obj_t *time_card_ = nullptr;" not in htext:
    anchor = "    lv_obj_t *chat_card_ = nullptr;"
    pos = htext.find(anchor)
    if pos < 0:
        raise SystemExit("Could not locate chat_card_ in custom_lcd_display.h")
    eol = htext.find("\n", pos)
    insert_at = eol + 1
    extra = (
        "    lv_obj_t *time_card_ = nullptr;\n"
        "    lv_obj_t *chat_text_box_ = nullptr;\n"
        "    lv_obj_t *chat_divider_ = nullptr;\n"
        "    lv_obj_t *avatar_img_ = nullptr;\n"
        "    bool chat_expanded_ = false;\n"
    )
    htext = htext[:insert_at] + extra + htext[insert_at:]

if "void SetChatExpandedInternal(bool expanded);" not in htext:
    anchor = "    void ApplyDisplayMode();\n"
    if anchor not in htext:
        raise SystemExit("Could not locate ApplyDisplayMode() in custom_lcd_display.h")
    htext = htext.replace(anchor, anchor + "    void SetChatExpandedInternal(bool expanded);\n", 1)

header.write_text(htext, encoding="utf-8")

# 2) Weather UI: retain object handles used when expanding/collapsing.
wtext = weather.read_text(encoding="utf-8")
if "time_card_ = time_card;" not in wtext:
    old = "    lv_obj_t *time_card = lv_obj_create(screen);\n"
    if old not in wtext:
        raise SystemExit("Could not locate time_card creation in weather_ui.cc")
    wtext = wtext.replace(old, old + "    time_card_ = time_card;\n", 1)

if "chat_divider_ = CreateDivider" not in wtext:
    old = "    CreateDivider(chat_card_, 8, 27, 126);"
    if old not in wtext:
        raise SystemExit("Could not locate chat divider in weather_ui.cc")
    wtext = wtext.replace(old, "    chat_divider_ = CreateDivider(chat_card_, 8, 27, 126);", 1)

if "chat_text_box_ = chat_text_box;" not in wtext:
    old = "    lv_obj_t *chat_text_box = lv_obj_create(chat_card_);\n"
    if old not in wtext:
        raise SystemExit("Could not locate chat_text_box creation in weather_ui.cc")
    wtext = wtext.replace(old, old + "    chat_text_box_ = chat_text_box;\n", 1)

if "avatar_img_ = avatar;" not in wtext:
    old = "    lv_obj_t *avatar = lv_image_create(screen);\n"
    if old not in wtext:
        raise SystemExit("Could not locate avatar creation in weather_ui.cc")
    wtext = wtext.replace(
        old,
        old + "    avatar_img_ = avatar;\n    lv_image_set_pivot(avatar_img_, 0, 0);\n    lv_image_set_antialias(avatar_img_, false);\n",
        1,
    )

weather.write_text(wtext, encoding="utf-8")

# 3) Custom display: restore immediate/original-style sentence display.
ctext = custom.read_text(encoding="utf-8")
start_marker = "void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {"
end_marker = "void CustomLcdDisplay::SetEmotion(const char* emotion) {"
start = ctext.find(start_marker)
end = ctext.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate SetChatMessage/SetEmotion in custom_lcd_display.cc")

new_chat_code = r'''void CustomLcdDisplay::SetChatExpandedInternal(bool expanded) {
    if (chat_expanded_ == expanded) return;
    chat_expanded_ = expanded;

    if (expanded) {
        if (time_card_) lv_obj_add_flag(time_card_, LV_OBJ_FLAG_HIDDEN);
        if (chat_card_) {
            lv_obj_set_pos(chat_card_, 8, 8);
            lv_obj_set_size(chat_card_, 274, 284);
        }
        if (chat_divider_) lv_obj_set_width(chat_divider_, 258);
        if (chat_text_box_) {
            lv_obj_set_pos(chat_text_box_, 8, 33);
            lv_obj_set_size(chat_text_box_, 204, 242);
        }
        if (chat_status_label_) {
            lv_obj_set_width(chat_status_label_, 204);
            lv_obj_set_style_text_line_space(chat_status_label_, 1, 0);
            lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        }
        if (avatar_img_) {
            lv_image_set_pivot(avatar_img_, 0, 0);
            lv_image_set_scale(avatar_img_, 96);
            lv_obj_set_pos(avatar_img_, 228, 178);
        }
    } else {
        if (time_card_) lv_obj_remove_flag(time_card_, LV_OBJ_FLAG_HIDDEN);
        if (chat_card_) {
            lv_obj_set_pos(chat_card_, 8, 116);
            lv_obj_set_size(chat_card_, 142, 176);
        }
        if (chat_divider_) lv_obj_set_width(chat_divider_, 126);
        if (chat_text_box_) {
            lv_obj_set_pos(chat_text_box_, 8, 33);
            lv_obj_set_size(chat_text_box_, 126, 134);
        }
        if (chat_status_label_) {
            lv_obj_set_width(chat_status_label_, 126);
            lv_obj_set_style_text_line_space(chat_status_label_, 3, 0);
            lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        }
        if (avatar_img_) {
            lv_image_set_pivot(avatar_img_, 0, 0);
            lv_image_set_scale(avatar_img_, 256);
            lv_obj_set_pos(avatar_img_, 154, 6);
        }
    }
}

void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {
    DisplayLockGuard lock(this);
    if (chat_status_label_ == nullptr && music_chat_status_label_ == nullptr) return;
    if (!content) return;

    if (chat_status_label_) lv_anim_delete(chat_status_label_, nullptr);
    SetShowingSystemInfo(false);

    const bool is_assistant = role && strcmp(role, "assistant") == 0;

    // Empty system message: clear and restore the manga home.
    if (content[0] == '\0') {
        SetChatExpandedInternal(false);
        if (chat_status_label_) lv_label_set_text(chat_status_label_, "");
        if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
        if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
        return;
    }

    // IMPORTANT: keep upstream/original semantics. The firmware calls this once
    // for each tts/sentence_start. Show THAT text immediately and do not append
    // it to older sentences. This is intentionally not a fake stream buffer.
    if (is_assistant) {
        SetChatExpandedInternal(true);
    } else {
        SetChatExpandedInternal(false);
    }

    if (chat_status_label_) {
        lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(chat_status_label_, content);
        lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        lv_obj_update_layout(chat_status_label_);

        // Most replies now fit because the dialog is much larger. If a single
        // server-delivered sentence is still too tall, use the original visual
        // idea (top-to-bottom scrolling), but only ONCE -- never loop forever.
        lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
        int visible_h = parent ? lv_obj_get_content_height(parent) : (chat_expanded_ ? 242 : 134);
        int label_h = lv_obj_get_height(chat_status_label_);
        if (label_h > visible_h) {
            lv_anim_t a;
            lv_anim_init(&a);
            lv_anim_set_var(&a, chat_status_label_);
            lv_anim_set_values(&a, 0, -(label_h - visible_h));
            lv_anim_set_delay(&a, 800);
            lv_anim_set_duration(&a, (label_h - visible_h) * 50);
            lv_anim_set_repeat_count(&a, 0);
            lv_anim_set_exec_cb(&a, [](void *obj, int32_t v) {
                lv_obj_set_y((lv_obj_t *)obj, v);
            });
            lv_anim_start(&a);
        }
    }

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

ctext = ctext[:start] + new_chat_code + ctext[end:]

# Make ClearChatMessages restore the normal home layout.
clear_start_marker = "void CustomLcdDisplay::ClearChatMessages() {"
clear_start = ctext.find(clear_start_marker)
if clear_start < 0:
    raise SystemExit("Could not locate ClearChatMessages in custom_lcd_display.cc")
clear_end = ctext.find("\n}\n", clear_start)
if clear_end < 0:
    raise SystemExit("Could not locate end of ClearChatMessages in custom_lcd_display.cc")
clear_end += 3
new_clear = r'''void CustomLcdDisplay::ClearChatMessages() {
    DisplayLockGuard lock(this);
    SetChatExpandedInternal(false);
    if (chat_status_label_) {
        lv_anim_delete(chat_status_label_, nullptr);
        lv_label_set_text(chat_status_label_, "");
    }
    if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
    if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
    // Keep the emotion visible.
}
'''
ctext = ctext[:clear_start] + new_clear + ctext[clear_end:]

custom.write_text(ctext, encoding="utf-8")

# 4) Data task: restore home after speaking ends. Keep only layout alignment and
# weather-text fixes. Do NOT alter scheduling, task priority, or protocol flow.
dtext = data.read_text(encoding="utf-8")
state_anchor = "            if (ds != last_ds) {\n"
if "last_ds == kDeviceStateSpeaking && ds != kDeviceStateSpeaking" not in dtext:
    if state_anchor not in dtext:
        raise SystemExit("Could not locate device-state transition block in data_update_task.cc")
    restore_code = (
        "            if (ds != last_ds) {\n"
        "                if (last_ds == kDeviceStateSpeaking && ds != kDeviceStateSpeaking) {\n"
        "                    self->SetChatExpandedInternal(false);\n"
        "                }\n"
    )
    dtext = dtext.replace(state_anchor, restore_code, 1)

old_align = "lv_obj_align(self->chat_status_label_, LV_ALIGN_LEFT_MID, 64 + 20, 0);"
if old_align in dtext:
    dtext = dtext.replace(old_align, "lv_obj_align(self->chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);", 1)

weather_re = re.compile(
    r'snprintf\(weather_buf, sizeof\(weather_buf\), "%s %s %s°C",\s*\n\s*wd\.city\.c_str\(\), wd\.text\.c_str\(\), wd\.temp\.c_str\(\)\);'
)
dtext, _ = weather_re.subn(
    'snprintf(weather_buf, sizeof(weather_buf), "%s %s°C",\n                 wd.text.c_str(), wd.temp.c_str());',
    dtext,
    count=1,
)

data.write_text(dtext, encoding="utf-8")
print("Xingyu V4: original-style immediate output + expanded chat applied successfully")
