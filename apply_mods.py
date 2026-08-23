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
app = root / "main" / "application.cc"

for path in (custom, header, data, weather, app):
    if not path.exists():
        raise SystemExit(f"required source not found: {path}")

# ---------------------------------------------------------------------------
# 1) Header: add pointers/state needed by the temporary expanded chat layout.
# ---------------------------------------------------------------------------
htext = header.read_text(encoding="utf-8")
if "std::string assistant_stream_text_;" not in htext:
    if "#include <string>" not in htext:
        htext = htext.replace("#include <atomic>\n", "#include <atomic>\n#include <string>\n", 1)

    anchor = "    lv_obj_t *chat_card_ = nullptr;         // AI card container\n"
    if anchor not in htext:
        # Upstream currently uses a Chinese comment, so match only the declaration.
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
            "    std::string assistant_stream_text_;\n"
            "    bool chat_expanded_ = false;\n"
        )
        htext = htext[:insert_at] + extra + htext[insert_at:]
    else:
        extra = (
            "    lv_obj_t *time_card_ = nullptr;\n"
            "    lv_obj_t *chat_text_box_ = nullptr;\n"
            "    lv_obj_t *chat_divider_ = nullptr;\n"
            "    lv_obj_t *avatar_img_ = nullptr;\n"
            "    std::string assistant_stream_text_;\n"
            "    bool chat_expanded_ = false;\n"
        )
        htext = htext.replace(anchor, anchor + extra, 1)

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
# 2) Weather UI: retain handles for the normal/expanded layout switch.
#    The user's overlay is copied here before this script runs.
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
        old + "    avatar_img_ = avatar;\n    lv_image_set_pivot(avatar_img_, 0, 0);\n    lv_image_set_antialias(avatar_img_, false);\n",
        1,
    )

weather.write_text(wtext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) Make LVGL responsive while TTS audio is playing.
#    Audio output runs at priority 4; LVGL upstream uses priority 2.
#    Raising LVGL to 3 keeps audio higher priority while preventing subtitle
#    redraws from being starved until speech is nearly finished.
# ---------------------------------------------------------------------------
ctext = custom.read_text(encoding="utf-8")
ctext = ctext.replace("port_cfg.task_priority = 2;", "port_cfg.task_priority = 3;", 1)
ctext = ctext.replace("port_cfg.timer_period_ms = 50;", "port_cfg.timer_period_ms = 20;", 1)
custom.write_text(ctext, encoding="utf-8")
# ---------------------------------------------------------------------------
# 3) Custom display: sentence-by-sentence accumulation + temporary large chat.
#    No pixel animation is used, which is important for the 1-bit RLCD.
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

        // Keep the character visible, but make her a small companion in the
        // lower-right corner of the expanded dialog.
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

    // Empty system messages are used by the application to clear the UI.
    if (content[0] == '\0') {
        assistant_stream_text_.clear();
        SetChatExpandedInternal(false);
        if (chat_status_label_) lv_label_set_text(chat_status_label_, "");
        if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
        if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
        return;
    }

    std::string display_text;
    if (is_assistant) {
        const std::string incoming(content);

        // The Xiaozhi protocol delivers TTS text at sentence_start. Usually each
        // callback is one new sentence. If a server ever sends cumulative text,
        // detect that too so we do not duplicate it.
        if (assistant_stream_text_.empty()) {
            assistant_stream_text_ = incoming;
        } else if (incoming.size() >= assistant_stream_text_.size() &&
                   incoming.compare(0, assistant_stream_text_.size(), assistant_stream_text_) == 0) {
            assistant_stream_text_ = incoming;
        } else if (assistant_stream_text_.size() < incoming.size() ||
                   assistant_stream_text_.compare(assistant_stream_text_.size() - incoming.size(),
                                                  incoming.size(), incoming) != 0) {
            assistant_stream_text_ += incoming;
        }

        // Keep RAM usage bounded. Trim only at an UTF-8 character boundary.
        const size_t kMaxBytes = 2400;
        if (assistant_stream_text_.size() > kMaxBytes) {
            size_t cut = assistant_stream_text_.size() - kMaxBytes;
            while (cut < assistant_stream_text_.size() &&
                   (static_cast<unsigned char>(assistant_stream_text_[cut]) & 0xC0) == 0x80) {
                ++cut;
            }
            assistant_stream_text_.erase(0, cut);
        }
        display_text = assistant_stream_text_;
    } else {
        // User/system text starts a new turn and returns to the normal manga home.
        assistant_stream_text_.clear();
        SetChatExpandedInternal(false);
        display_text = content;
    }

    if (chat_status_label_) {
        lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
        lv_label_set_text(chat_status_label_, display_text.c_str());
        lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
        lv_obj_update_layout(chat_status_label_);

        // Only expand when the accumulated assistant reply no longer fits in the
        // normal 126 x 134 dialog. Short answers keep the original home screen.
        if (is_assistant && !chat_expanded_) {
            lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
            int visible_h = parent ? lv_obj_get_content_height(parent) : 134;
            if (lv_obj_get_height(chat_status_label_) > visible_h) {
                SetChatExpandedInternal(true);
                lv_label_set_text(chat_status_label_, display_text.c_str());
                lv_obj_update_layout(chat_status_label_);
            }
        }

        // Follow the newest lines without any animation. Each incoming sentence
        // causes only one static RLCD update, so it feels progressive but does not
        // hammer the reflective panel with per-pixel scrolling.
        lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
        int visible_h = parent ? lv_obj_get_content_height(parent) : (chat_expanded_ ? 242 : 134);
        int label_h = lv_obj_get_height(chat_status_label_);
        if (label_h > visible_h) {
            lv_obj_set_y(chat_status_label_, visible_h - label_h);
        } else {
            lv_obj_set_y(chat_status_label_, 0);
        }
    }

    // Other pages keep their existing compact behavior.
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

# Replace ClearChatMessages so an interrupted/finished turn always restores home.
clear_start_marker = "void CustomLcdDisplay::ClearChatMessages() {"
clear_end_marker = "// ====="
clear_start = ctext.find(clear_start_marker)
if clear_start < 0:
    raise SystemExit("Could not locate ClearChatMessages in custom_lcd_display.cc")
clear_end = ctext.find(clear_end_marker, clear_start + len(clear_start_marker))
if clear_end < 0:
    raise SystemExit("Could not locate end of ClearChatMessages in custom_lcd_display.cc")

new_clear = r'''void CustomLcdDisplay::ClearChatMessages() {
    DisplayLockGuard lock(this);
    assistant_stream_text_.clear();
    SetChatExpandedInternal(false);
    if (chat_status_label_) lv_label_set_text(chat_status_label_, "");
    if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
    if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
    // Keep the emotion visible.
}

'''
ctext = ctext[:clear_start] + new_clear + ctext[clear_end:]
custom.write_text(ctext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4) Protocol/UI timing: never leave the screen blank when TTS starts.
#    Xiaozhi sends the actual subtitle text only in tts/sentence_start.
#    Show an immediate placeholder on tts/start; each sentence_start then
#    updates the accumulated reply as soon as the server sends it.
# ---------------------------------------------------------------------------
atext = app.read_text(encoding="utf-8")
old_tts_start = (
    "            Schedule([this]() {\n"
    "                aborted_ = false;\n"
    "                SetDeviceState(kDeviceStateSpeaking);\n"
    "            });"
)
new_tts_start = (
    "            Schedule([this, display]() {\n"
    "                aborted_ = false;\n"
    "                SetDeviceState(kDeviceStateSpeaking);\n"
    "                display->SetChatMessage(\"system\", \"正在回复…\");\n"
    "            });"
)
if old_tts_start in atext:
    atext = atext.replace(old_tts_start, new_tts_start, 1)
elif 'display->SetChatMessage("system", "正在回复…");' not in atext:
    print("warning: tts/start block not found; continuing without placeholder patch")
app.write_text(atext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 5) Data task: restore the manga home as soon as speaking ends, and keep the
#    current Xingyu status/weather alignment fixes.
# ---------------------------------------------------------------------------
dtext = data.read_text(encoding="utf-8")

state_anchor = "            if (ds != last_ds) {\n"
if "last_ds == kDeviceStateSpeaking" not in dtext:
    if state_anchor not in dtext:
        raise SystemExit("Could not locate device-state transition block in data_update_task.cc")
    restore_code = (
        "            if (ds != last_ds) {\n"
        "                if (last_ds == kDeviceStateSpeaking && ds != kDeviceStateSpeaking) {\n"
        "                    self->assistant_stream_text_.clear();\n"
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
print("Xingyu streaming chat v3 modifications applied successfully")
