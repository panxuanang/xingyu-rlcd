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

# Xingyu V5
# - Keep the dynamic large chat panel and small companion avatar.
# - Do NOT render a giant assistant paragraph in one LVGL label update.
# - Split every incoming assistant payload locally into short sentence/clause chunks.
# - Show the first chunk immediately, then append short chunks one by one.
# - No pixel scrolling and no infinite animation: suitable for 1-bit RLCD.

# ---------------------------------------------------------------------------
# 1) Header: dynamic layout + local sentence queue.
# ---------------------------------------------------------------------------
htext = header.read_text(encoding="utf-8")
if "#include <deque>" not in htext:
    if "#include <atomic>\n" in htext:
        htext = htext.replace("#include <atomic>\n", "#include <atomic>\n#include <deque>\n#include <string>\n", 1)
    else:
        htext = htext.replace("#define __CUSTOM_LCD_DISPLAY_H__\n", "#define __CUSTOM_LCD_DISPLAY_H__\n#include <deque>\n#include <string>\n", 1)

if "chat_sentence_queue_" not in htext:
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
        "    std::deque<std::string> chat_sentence_queue_;\n"
        "    std::string chat_history_;\n"
        "    lv_timer_t *chat_sentence_timer_ = nullptr;\n"
        "    bool chat_expanded_ = false;\n"
    )
    htext = htext[:insert_at] + extra + htext[insert_at:]

method_anchor = "    void ApplyDisplayMode();\n"
methods = (
    "    void SetChatExpandedInternal(bool expanded);\n"
    "    void QueueAssistantSentenceChunks(const char *content);\n"
    "    void ShowNextAssistantSentenceChunk();\n"
    "    void ResetAssistantSentenceChunks();\n"
    "    static void ChatSentenceTimerCallback(lv_timer_t *timer);\n"
)
if "QueueAssistantSentenceChunks" not in htext:
    if method_anchor not in htext:
        raise SystemExit("Could not locate ApplyDisplayMode() in custom_lcd_display.h")
    htext = htext.replace(method_anchor, method_anchor + methods, 1)

header.write_text(htext, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Weather UI: retain handles for normal/expanded layout.
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
# 3) Custom display: WeChat-like local sentence feed.
# ---------------------------------------------------------------------------
ctext = custom.read_text(encoding="utf-8")
start_marker = "void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {"
end_marker = "void CustomLcdDisplay::SetEmotion(const char* emotion) {"
start = ctext.find(start_marker)
end = ctext.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate SetChatMessage/SetEmotion in custom_lcd_display.cc")

new_chat_code = r'''static size_t XingyuUtf8CharLen(unsigned char c) {
    if ((c & 0x80) == 0x00) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

static bool XingyuIsStrongBreak(const std::string& cp) {
    return cp == "。" || cp == "！" || cp == "？" || cp == "；" ||
           cp == "." || cp == "!" || cp == "?" || cp == ";" || cp == "\n";
}

static bool XingyuIsWeakBreak(const std::string& cp) {
    return cp == "，" || cp == "," || cp == "、" || cp == "：" || cp == ":";
}

void CustomLcdDisplay::SetChatExpandedInternal(bool expanded) {
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

void CustomLcdDisplay::ResetAssistantSentenceChunks() {
    if (chat_sentence_timer_) {
        lv_timer_delete(chat_sentence_timer_);
        chat_sentence_timer_ = nullptr;
    }
    chat_sentence_queue_.clear();
    chat_history_.clear();
}

void CustomLcdDisplay::QueueAssistantSentenceChunks(const char *content) {
    if (!content || content[0] == '\0') return;

    std::string text(content);
    std::string chunk;
    int char_count = 0;

    // Split at normal Chinese sentence punctuation. If the server sends one very
    // long run-on paragraph, force a cut around 20 glyphs so the first RLCD draw
    // stays small and quick.
    for (size_t i = 0; i < text.size();) {
        size_t cp_len = XingyuUtf8CharLen(static_cast<unsigned char>(text[i]));
        if (i + cp_len > text.size()) cp_len = 1;
        std::string cp = text.substr(i, cp_len);
        i += cp_len;

        chunk += cp;
        ++char_count;

        const bool strong_break = XingyuIsStrongBreak(cp);
        const bool weak_break = XingyuIsWeakBreak(cp) && char_count >= 10;
        const bool hard_break = char_count >= 20;
        if (strong_break || weak_break || hard_break) {
            if (!chunk.empty() && chunk != "\n") chat_sentence_queue_.push_back(chunk);
            chunk.clear();
            char_count = 0;
        }
    }

    if (!chunk.empty()) chat_sentence_queue_.push_back(chunk);
}

void CustomLcdDisplay::ShowNextAssistantSentenceChunk() {
    if (chat_sentence_queue_.empty() || !chat_status_label_) return;

    std::string chunk = std::move(chat_sentence_queue_.front());
    chat_sentence_queue_.pop_front();

    if (!chat_history_.empty()) chat_history_ += "\n";
    chat_history_ += chunk;

    // Bound retained text. This is a chat feed: older lines naturally move off
    // the top, while the latest several short sentences remain visible.
    const size_t kMaxHistoryBytes = 1000;
    if (chat_history_.size() > kMaxHistoryBytes) {
        size_t cut = chat_history_.size() - kMaxHistoryBytes;
        while (cut < chat_history_.size() &&
               (static_cast<unsigned char>(chat_history_[cut]) & 0xC0) == 0x80) {
            ++cut;
        }
        chat_history_.erase(0, cut);
    }

    lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
    lv_label_set_text(chat_status_label_, chat_history_.c_str());
    lv_obj_update_layout(chat_status_label_);

    lv_obj_t *parent = lv_obj_get_parent(chat_status_label_);
    int visible_h = parent ? lv_obj_get_content_height(parent) : 242;
    int label_h = lv_obj_get_height(chat_status_label_);
    lv_obj_set_y(chat_status_label_, label_h > visible_h ? visible_h - label_h : 0);
}

void CustomLcdDisplay::ChatSentenceTimerCallback(lv_timer_t *timer) {
    auto *self = static_cast<CustomLcdDisplay *>(lv_timer_get_user_data(timer));
    if (!self) {
        lv_timer_delete(timer);
        return;
    }

    if (self->chat_sentence_queue_.empty()) {
        self->chat_sentence_timer_ = nullptr;
        lv_timer_delete(timer);
        return;
    }

    self->ShowNextAssistantSentenceChunk();

    if (self->chat_sentence_queue_.empty()) {
        self->chat_sentence_timer_ = nullptr;
        lv_timer_delete(timer);
    } else {
        // Whole-line updates are much friendlier to RLCD than pixel scrolling.
        // ~0.8 s gives a WeChat/subtitle-like rhythm without hammering the panel.
        lv_timer_set_period(timer, 800);
    }
}

void CustomLcdDisplay::SetChatMessage(const char* role, const char* content) {
    DisplayLockGuard lock(this);
    if (chat_status_label_ == nullptr && music_chat_status_label_ == nullptr) return;
    if (!content) return;

    if (chat_status_label_) lv_anim_delete(chat_status_label_, nullptr);
    SetShowingSystemInfo(false);

    const bool is_assistant = role && strcmp(role, "assistant") == 0;

    if (content[0] == '\0') {
        ResetAssistantSentenceChunks();
        SetChatExpandedInternal(false);
        if (chat_status_label_) lv_label_set_text(chat_status_label_, "");
        if (music_chat_status_label_) lv_label_set_text(music_chat_status_label_, "");
        if (pomo_chat_status_label_) lv_label_set_text(pomo_chat_status_label_, "");
        return;
    }

    if (is_assistant) {
        SetChatExpandedInternal(true);
        QueueAssistantSentenceChunks(content);

        // Key behavior: render the first small sentence immediately instead of
        // asking LVGL/RLCD to lay out one huge paragraph first.
        if (!chat_sentence_timer_) {
            ShowNextAssistantSentenceChunk();
            if (!chat_sentence_queue_.empty()) {
                chat_sentence_timer_ = lv_timer_create(ChatSentenceTimerCallback, 800, this);
            }
        }
    } else {
        ResetAssistantSentenceChunks();
        SetChatExpandedInternal(false);
        if (chat_status_label_) {
            lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
            lv_label_set_text(chat_status_label_, content);
            lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
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

# Clear chat should also stop the local sentence timer/feed.
clear_start_marker = "void CustomLcdDisplay::ClearChatMessages() {"
clear_start = ctext.find(clear_start_marker)
if clear_start < 0:
    raise SystemExit("Could not locate ClearChatMessages in custom_lcd_display.cc")

# Prefer a nearby board section marker, fall back to the closing brace.
clear_end_marker = "// ====="
clear_end = ctext.find(clear_end_marker, clear_start + len(clear_start_marker))
if clear_end < 0:
    clear_end = ctext.find("\n}\n", clear_start)
    if clear_end < 0:
        raise SystemExit("Could not locate end of ClearChatMessages in custom_lcd_display.cc")
    clear_end += 3

new_clear = r'''void CustomLcdDisplay::ClearChatMessages() {
    DisplayLockGuard lock(this);
    ResetAssistantSentenceChunks();
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

# ---------------------------------------------------------------------------
# 4) Data task: restore home after speaking ends + keep current alignment/weather.
# ---------------------------------------------------------------------------
dtext = data.read_text(encoding="utf-8")
state_anchor = "            if (ds != last_ds) {\n"
if "ResetAssistantSentenceChunks();" not in dtext:
    if state_anchor not in dtext:
        raise SystemExit("Could not locate device-state transition block in data_update_task.cc")
    restore_code = (
        "            if (ds != last_ds) {\n"
        "                if (last_ds == kDeviceStateSpeaking && ds != kDeviceStateSpeaking) {\n"
        "                    self->ResetAssistantSentenceChunks();\n"
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
print("Xingyu V5: WeChat-like local sentence chunks + expanded RLCD chat applied successfully")
