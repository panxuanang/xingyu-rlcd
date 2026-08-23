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

# Xingyu V6
# - Keep the current Xingyu manga dashboard.
# - Restore the original-style continuous text movement for long replies.
# - Long assistant replies automatically expand the chat panel.
# - The time card hides and the avatar shrinks/moves aside while expanded.
# - Scroll once from top to bottom, then stop (no infinite repeat).
# - Restore the normal home layout when speaking ends / chat is cleared.

# ---------------------------------------------------------------------------
# 1) Header: handles needed by the dynamic chat layout.
# ---------------------------------------------------------------------------
htext = header.read_text(encoding="utf-8")

if "chat_expanded_" not in htext:
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

if "SetChatExpandedInternal" not in htext:
    method_anchor = "    void ApplyDisplayMode();\n"
    if method_anchor not in htext:
        raise SystemExit("Could not locate ApplyDisplayMode() in custom_lcd_display.h")
    htext = htext.replace(
        method_anchor,
        method_anchor + "    void SetChatExpandedInternal(bool expanded);\n",
        1,
    )

header.write_text(htext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Weather UI: keep object handles so SetChatMessage can resize the layout.
# ---------------------------------------------------------------------------
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
        old
        + "    avatar_img_ = avatar;\n"
        + "    lv_image_set_pivot(avatar_img_, 0, 0);\n"
        + "    lv_image_set_antialias(avatar_img_, false);\n",
        1,
    )

weather.write_text(wtext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) Custom display: dynamic big chat + original-style one-way scrolling.
# ---------------------------------------------------------------------------
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

    if (chat_status_label_) {
        lv_anim_delete(chat_status_label_, nullptr);
        lv_obj_set_y(chat_status_label_, 0);
    }

    if (expanded) {
        // Large answer mode: use almost all of the left + center area.
        if (time_card_) lv_obj_add_flag(time_card_, LV_OBJ_FLAG_HIDDEN);

        if (chat_card_) {
            lv_obj_set_pos(chat_card_, 8, 8);
            lv_obj_set_size(chat_card_, 274, 284);
        }

        if (chat_divider_) lv_obj_set_width(chat_divider_, 258);

        // Leave a narrow strip on the right for the shrunken companion avatar.
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
            lv_image_set_scale(avatar_img_, 96);   // 37.5%
            lv_obj_set_pos(avatar_img_, 228, 178);
            lv_obj_move_foreground(avatar_img_);
        }
    } else {
        // Restore the normal Xingyu dashboard.
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
            lv_obj_move_foreground(avatar_img_);
        }
    }
}

void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {
    DisplayLockGuard lock(this);

    if (chat_status_label_ == nullptr && music_chat_status_label_ == nullptr) return;
    if (!content || content[0] == '\0') return;

    SetShowingSystemInfo(false);

    const bool is_assistant = role && strcmp(role, "assistant") == 0;

    if (chat_status_label_) {
        // Stop any previous scroll before replacing the text.
        lv_anim_delete(chat_status_label_, nullptr);
        lv_obj_set_y(chat_status_label_, 0);
        lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(chat_status_label_, content);
        lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        lv_obj_update_layout(chat_status_label_);

        // First measure the answer in the normal compact box.  If it is long,
        // expand once and keep the large panel until speaking ends.
        lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
        int visible_h = parent ? lv_obj_get_content_height(parent) : 134;
        int label_h = lv_obj_get_height(chat_status_label_);

        if (is_assistant && !chat_expanded_ && label_h > visible_h) {
            SetChatExpandedInternal(true);
            lv_obj_update_layout(chat_status_label_);
            parent = lv_obj_get_parent(chat_status_label_);
            visible_h = parent ? lv_obj_get_content_height(parent) : 242;
            label_h = lv_obj_get_height(chat_status_label_);
        }

        // If a user message arrives, go back to the normal dashboard.
        if (!is_assistant && chat_expanded_) {
            SetChatExpandedInternal(false);
            lv_obj_update_layout(chat_status_label_);
            parent = lv_obj_get_parent(chat_status_label_);
            visible_h = parent ? lv_obj_get_content_height(parent) : 134;
            label_h = lv_obj_get_height(chat_status_label_);
        }

        if (label_h > visible_h) {
            // Restore the feel of the original firmware: continuous movement
            // from the beginning of the answer down to the final lines.
            // Unlike the original, it runs only once and does not restart.
            const int distance = label_h - visible_h;
            int duration = distance * 22;  // faster than original 50 ms/pixel
            if (duration < 1200) duration = 1200;
            if (duration > 12000) duration = 12000;

            lv_anim_t a;
            lv_anim_init(&a);
            lv_anim_set_var(&a, chat_status_label_);
            lv_anim_set_values(&a, 0, -distance);
            lv_anim_set_delay(&a, 300);
            lv_anim_set_duration(&a, duration);
            lv_anim_set_exec_cb(&a, [](void *obj, int32_t v) {
                lv_obj_set_y((lv_obj_t *)obj, v);
            });
            lv_anim_start(&a);

            ESP_LOGI(TAG,
                     "Xingyu long answer: %dpx > %dpx, scroll once in %dms",
                     label_h, visible_h, duration);
        }
    }

    // Keep the other pages in sync with the current payload.
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

# Clear chat must also restore the normal dashboard.
clear_start_marker = "void CustomLcdDisplay::ClearChatMessages() {"
clear_start = ctext.find(clear_start_marker)
if clear_start < 0:
    raise SystemExit("Could not locate ClearChatMessages in custom_lcd_display.cc")
clear_end_marker = "// ====="
clear_end = ctext.find(clear_end_marker, clear_start + len(clear_start_marker))
if clear_end < 0:
    clear_end = ctext.find("\n}\n", clear_start)
    if clear_end < 0:
        raise SystemExit("Could not locate end of ClearChatMessages in custom_lcd_display.cc")
    clear_end += 3

new_clear = r'''void CustomLcdDisplay::ClearChatMessages() {
    DisplayLockGuard lock(this);
    if (chat_status_label_) {
        lv_anim_delete(chat_status_label_, nullptr);
        lv_obj_set_y(chat_status_label_, 0);
        lv_label_set_text(chat_status_label_, "");
    }
    SetChatExpandedInternal(false);
    if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
    if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
    // Keep the emotion visible.
}

'''

ctext = ctext[:clear_start] + new_clear + ctext[clear_end:]
custom.write_text(ctext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4) Data task: restore home when speaking ends + keep Xingyu alignment/weather.
# ---------------------------------------------------------------------------
dtext = data.read_text(encoding="utf-8")

state_anchor = "            if (ds != last_ds) {\n"
restore_signature = "last_ds == kDeviceStateSpeaking && ds != kDeviceStateSpeaking"
if restore_signature not in dtext:
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
    dtext = dtext.replace(
        old_align,
        "lv_obj_align(self->chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);",
        1,
    )

weather_re = re.compile(
    r'snprintf\(weather_buf, sizeof\(weather_buf\), "%s %s %s°C",\s*\n\s*wd\.city\.c_str\(\), wd\.text\.c_str\(\), wd\.temp\.c_str\(\)\);'
)
dtext, _ = weather_re.subn(
    'snprintf(weather_buf, sizeof(weather_buf), "%s %s°C",\n                 wd.text.c_str(), wd.temp.c_str());',
    dtext,
    count=1,
)

data.write_text(dtext, encoding="utf-8")
print("Xingyu V6: expanded chat + one-way continuous RLCD scrolling applied successfully")
