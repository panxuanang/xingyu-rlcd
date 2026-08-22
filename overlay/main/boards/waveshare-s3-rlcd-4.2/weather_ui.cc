// 星语伴侣 - 400x300 RLCD manga dashboard
// Replace: main/boards/waveshare-s3-rlcd-4.2/weather_ui.cc
#include "custom_lcd_display.h"
#include <esp_log.h>

LV_FONT_DECLARE(alibaba_puhui_16);
LV_FONT_DECLARE(alibaba_puhui_48);
LV_FONT_DECLARE(font_puhui_16_4);
LV_FONT_DECLARE(font_puhui_14_1);

LV_IMAGE_DECLARE(ui_img_wifi);
LV_IMAGE_DECLARE(ui_img_wifi_low);
LV_IMAGE_DECLARE(ui_img_wifi_off);
LV_IMAGE_DECLARE(ui_img_battery_full);
LV_IMAGE_DECLARE(ui_img_battery_medium);
LV_IMAGE_DECLARE(ui_img_battery_low);
LV_IMAGE_DECLARE(ui_img_battery_charging);
LV_IMAGE_DECLARE(ui_img_xingyu_girl);

static const char *TAG = "WeatherUI";

static void StyleCard(lv_obj_t *obj, int radius = 10) {
    lv_obj_set_style_bg_color(obj, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(obj, 2, 0);
    lv_obj_set_style_border_color(obj, lv_color_black(), 0);
    lv_obj_set_style_radius(obj, radius, 0);
    lv_obj_set_style_pad_all(obj, 0, 0);
    lv_obj_remove_flag(obj, LV_OBJ_FLAG_SCROLLABLE);
}

static lv_obj_t *CreateDivider(lv_obj_t *parent, int x, int y, int width) {
    lv_obj_t *line = lv_obj_create(parent);
    lv_obj_set_pos(line, x, y);
    lv_obj_set_size(line, width, 1);
    lv_obj_set_style_bg_color(line, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(line, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(line, 0, 0);
    lv_obj_set_style_radius(line, 0, 0);
    lv_obj_set_style_pad_all(line, 0, 0);
    lv_obj_remove_flag(line, LV_OBJ_FLAG_SCROLLABLE);
    return line;
}

void CustomLcdDisplay::SetupWeatherUI() {
    DisplayLockGuard lock(this);

    lv_obj_t *root = lv_screen_active();
    lv_obj_set_style_bg_color(root, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(root, LV_OPA_COVER, 0);

    weather_page_ = lv_obj_create(root);
    lv_obj_set_size(weather_page_, 400, 300);
    lv_obj_set_pos(weather_page_, 0, 0);
    lv_obj_set_style_bg_color(weather_page_, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(weather_page_, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(weather_page_, 0, 0);
    lv_obj_set_style_pad_all(weather_page_, 0, 0);
    lv_obj_set_style_radius(weather_page_, 0, 0);
    lv_obj_remove_flag(weather_page_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *screen = weather_page_;

    const lv_font_t *font_small = &alibaba_puhui_16;
    const lv_font_t *font_large = &alibaba_puhui_48;
    const lv_font_t *font_ai = &font_puhui_16_4;
    const lv_font_t *font_tiny = &font_puhui_14_1;

    // Outer manga frame.
    lv_obj_t *frame = lv_obj_create(screen);
    lv_obj_set_pos(frame, 2, 2);
    lv_obj_set_size(frame, 396, 296);
    lv_obj_set_style_bg_opa(frame, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(frame, 2, 0);
    lv_obj_set_style_border_color(frame, lv_color_black(), 0);
    lv_obj_set_style_radius(frame, 12, 0);
    lv_obj_set_style_pad_all(frame, 0, 0);
    lv_obj_remove_flag(frame, LV_OBJ_FLAG_SCROLLABLE);

    // ===== Left top: time/date/weather =====
    lv_obj_t *time_card = lv_obj_create(screen);
    lv_obj_set_pos(time_card, 8, 8);
    lv_obj_set_size(time_card, 142, 104);
    StyleCard(time_card, 10);

    day_label_ = lv_label_create(time_card);
    lv_obj_set_style_text_font(day_label_, font_tiny, 0);
    lv_obj_set_style_text_color(day_label_, lv_color_black(), 0);
    lv_obj_set_pos(day_label_, 8, 4);
    lv_label_set_text(day_label_, "---");

    date_num_label_ = lv_label_create(time_card);
    lv_obj_set_style_text_font(date_num_label_, font_small, 0);
    lv_obj_set_style_text_color(date_num_label_, lv_color_black(), 0);
    lv_obj_set_style_text_align(date_num_label_, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_set_width(date_num_label_, 72);
    lv_obj_align(date_num_label_, LV_ALIGN_TOP_RIGHT, -8, 4);
    lv_label_set_text(date_num_label_, "--");

    time_label_ = lv_label_create(time_card);
    lv_obj_set_style_text_font(time_label_, font_large, 0);
    lv_obj_set_style_text_color(time_label_, lv_color_black(), 0);
    lv_obj_set_style_text_letter_space(time_label_, 0, 0);
    lv_obj_set_width(time_label_, 134);
    lv_obj_set_style_text_align(time_label_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(time_label_, LV_ALIGN_TOP_MID, 0, 23);
    lv_label_set_text(time_label_, "00:00");

    CreateDivider(time_card, 8, 77, 126);

    weather_label_ = lv_label_create(time_card);
    lv_obj_set_style_text_font(weather_label_, font_small, 0);
    lv_obj_set_style_text_color(weather_label_, lv_color_black(), 0);
    lv_obj_set_width(weather_label_, 126);
    lv_obj_set_style_text_align(weather_label_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(weather_label_, LV_ALIGN_BOTTOM_MID, 0, -5);
    lv_label_set_text(weather_label_, "-- --°C");

    // ===== Left bottom: enlarged AI dialog =====
    chat_card_ = lv_obj_create(screen);
    lv_obj_set_pos(chat_card_, 8, 116);
    lv_obj_set_size(chat_card_, 142, 176);
    StyleCard(chat_card_, 10);
    lv_obj_set_style_clip_corner(chat_card_, true, 0);

    lv_obj_t *chat_title = lv_label_create(chat_card_);
    lv_obj_set_style_text_font(chat_title, font_ai, 0);
    lv_obj_set_style_text_color(chat_title, lv_color_black(), 0);
    lv_obj_set_pos(chat_title, 9, 4);
    lv_label_set_text(chat_title, "AI");

    emotion_label_ = lv_label_create(chat_card_);
    lv_obj_set_style_text_font(emotion_label_, font_tiny, 0);
    lv_obj_set_style_text_color(emotion_label_, lv_color_black(), 0);
    lv_obj_set_style_text_align(emotion_label_, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_set_width(emotion_label_, 78);
    lv_obj_align(emotion_label_, LV_ALIGN_TOP_RIGHT, -9, 5);
    lv_label_set_text(emotion_label_, "待命");

    CreateDivider(chat_card_, 8, 27, 126);

    // Dedicated clipping container for long AI replies.
    // SetChatMessage should align chat_status_label_ at x=0, y=0 in this container.
    lv_obj_t *chat_text_box = lv_obj_create(chat_card_);
    lv_obj_set_pos(chat_text_box, 8, 33);
    lv_obj_set_size(chat_text_box, 126, 134);
    lv_obj_set_style_bg_opa(chat_text_box, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(chat_text_box, 0, 0);
    lv_obj_set_style_pad_all(chat_text_box, 0, 0);
    lv_obj_set_style_radius(chat_text_box, 0, 0);
    lv_obj_set_style_clip_corner(chat_text_box, true, 0);
    lv_obj_remove_flag(chat_text_box, LV_OBJ_FLAG_SCROLLABLE);

    chat_status_label_ = lv_label_create(chat_text_box);
    lv_obj_set_style_text_font(chat_status_label_, font_ai, 0);
    lv_obj_set_style_text_color(chat_status_label_, lv_color_black(), 0);
    lv_obj_set_style_text_align(chat_status_label_, LV_TEXT_ALIGN_LEFT, 0);
    lv_obj_set_width(chat_status_label_, 126);
    lv_obj_set_style_text_line_space(chat_status_label_, 3, 0);
    lv_label_set_long_mode(chat_status_label_, LV_LABEL_LONG_WRAP);
    lv_obj_align(chat_status_label_, LV_ALIGN_TOP_LEFT, 0, 0);
    lv_label_set_text(chat_status_label_, "你好呀~\n今天也一起加油吧！");

    // Keep weather-page emoji image unused so SetEmotion never replaces the fixed avatar.
    emotion_img_ = nullptr;

    // ===== Center: fixed manga avatar =====
    lv_obj_t *avatar = lv_image_create(screen);
    lv_image_set_src(avatar, &ui_img_xingyu_girl);
    lv_obj_set_pos(avatar, 154, 6);

    // Small manga decoration marks around avatar without extra bitmap assets.
    lv_obj_t *sparkle1 = lv_label_create(screen);
    lv_obj_set_style_text_font(sparkle1, font_small, 0);
    lv_obj_set_style_text_color(sparkle1, lv_color_black(), 0);
    lv_obj_set_pos(sparkle1, 158, 26);
    lv_label_set_text(sparkle1, "+");

    lv_obj_t *sparkle2 = lv_label_create(screen);
    lv_obj_set_style_text_font(sparkle2, font_small, 0);
    lv_obj_set_style_text_color(sparkle2, lv_color_black(), 0);
    lv_obj_set_pos(sparkle2, 266, 18);
    lv_label_set_text(sparkle2, "+");

    // ===== Right: product identity =====
    lv_obj_t *brand = lv_label_create(screen);
    lv_obj_set_style_text_font(brand, font_ai, 0);
    lv_obj_set_style_text_color(brand, lv_color_black(), 0);
    lv_obj_set_width(brand, 104);
    lv_obj_set_style_text_align(brand, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_pos(brand, 286, 8);
    lv_label_set_text(brand, "星语伴侣");

    lv_obj_t *brand_en = lv_label_create(screen);
    lv_obj_set_style_text_font(brand_en, font_tiny, 0);
    lv_obj_set_style_text_color(brand_en, lv_color_black(), 0);
    lv_obj_set_width(brand_en, 104);
    lv_obj_set_style_text_align(brand_en, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_pos(brand_en, 286, 29);
    lv_label_set_text(brand_en, "STELLAR AI");

    lv_obj_t *brand_line = lv_obj_create(screen);
    lv_obj_set_pos(brand_line, 292, 49);
    lv_obj_set_size(brand_line, 92, 2);
    lv_obj_set_style_bg_color(brand_line, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(brand_line, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(brand_line, 0, 0);
    lv_obj_set_style_pad_all(brand_line, 0, 0);
    lv_obj_remove_flag(brand_line, LV_OBJ_FLAG_SCROLLABLE);

    // ===== Right middle: status card =====
    lv_obj_t *status_card = lv_obj_create(screen);
    lv_obj_set_pos(status_card, 286, 57);
    lv_obj_set_size(status_card, 106, 113);
    StyleCard(status_card, 10);

    lv_obj_t *status_title = lv_label_create(status_card);
    lv_obj_set_style_text_font(status_title, font_ai, 0);
    lv_obj_set_style_text_color(status_title, lv_color_black(), 0);
    lv_obj_set_pos(status_title, 7, 4);
    lv_label_set_text(status_title, "状态");
    CreateDivider(status_card, 7, 25, 92);

    wifi_icon_img_ = lv_image_create(status_card);
    lv_image_set_src(wifi_icon_img_, &ui_img_wifi_off);
    lv_obj_set_pos(wifi_icon_img_, 7, 31);

    lv_obj_t *wifi_text = lv_label_create(status_card);
    lv_obj_set_style_text_font(wifi_text, font_tiny, 0);
    lv_obj_set_style_text_color(wifi_text, lv_color_black(), 0);
    lv_obj_set_pos(wifi_text, 35, 32);
    lv_label_set_text(wifi_text, "Wi-Fi");

    battery_icon_img_ = lv_image_create(status_card);
    lv_image_set_src(battery_icon_img_, &ui_img_battery_full);
    lv_obj_set_pos(battery_icon_img_, 7, 57);

    battery_pct_label_ = lv_label_create(status_card);
    lv_obj_set_style_text_font(battery_pct_label_, font_tiny, 0);
    lv_obj_set_style_text_color(battery_pct_label_, lv_color_black(), 0);
    lv_obj_set_pos(battery_pct_label_, 35, 58);
    lv_label_set_text(battery_pct_label_, "---%");

    sensor_label_ = lv_label_create(status_card);
    lv_obj_set_style_text_font(sensor_label_, font_tiny, 0);
    lv_obj_set_style_text_color(sensor_label_, lv_color_black(), 0);
    lv_obj_set_width(sensor_label_, 94);
    lv_obj_set_style_text_align(sensor_label_, LV_TEXT_ALIGN_LEFT, 0);
    lv_obj_set_pos(sensor_label_, 7, 84);
    lv_label_set_text(sensor_label_, "--.-°C  --.-%");

    // ===== Right bottom: reminders =====
    lv_obj_t *memo_card = lv_obj_create(screen);
    lv_obj_set_pos(memo_card, 286, 176);
    lv_obj_set_size(memo_card, 106, 116);
    StyleCard(memo_card, 10);

    lv_obj_t *memo_title = lv_label_create(memo_card);
    lv_obj_set_style_text_font(memo_title, font_ai, 0);
    lv_obj_set_style_text_color(memo_title, lv_color_black(), 0);
    lv_obj_set_pos(memo_title, 7, 4);
    lv_label_set_text(memo_title, "今日提醒");
    CreateDivider(memo_card, 7, 26, 92);

    memo_list_label_ = lv_label_create(memo_card);
    lv_obj_set_style_text_font(memo_list_label_, font_tiny, 0);
    lv_obj_set_style_text_color(memo_list_label_, lv_color_black(), 0);
    lv_obj_set_style_text_align(memo_list_label_, LV_TEXT_ALIGN_LEFT, 0);
    lv_obj_set_width(memo_list_label_, 92);
    lv_obj_set_height(memo_list_label_, 78);
    lv_label_set_long_mode(memo_list_label_, LV_LABEL_LONG_CLIP);
    lv_obj_set_pos(memo_list_label_, 7, 33);
    lv_label_set_text(memo_list_label_, "暂无待办");

    // ===== Hidden placeholders required by LcdDisplay base-class methods =====
    container_ = lv_obj_create(screen);
    lv_obj_set_size(container_, 1, 1);
    lv_obj_add_flag(container_, LV_OBJ_FLAG_HIDDEN);

    network_label_ = lv_label_create(screen);
    lv_label_set_text(network_label_, "");
    lv_obj_add_flag(network_label_, LV_OBJ_FLAG_HIDDEN);

    battery_label_ = lv_label_create(screen);
    lv_label_set_text(battery_label_, "");
    lv_obj_add_flag(battery_label_, LV_OBJ_FLAG_HIDDEN);

    status_label_ = lv_label_create(screen);
    lv_label_set_text(status_label_, "");
    lv_obj_add_flag(status_label_, LV_OBJ_FLAG_HIDDEN);

    notification_label_ = lv_label_create(screen);
    lv_label_set_text(notification_label_, "");
    lv_obj_add_flag(notification_label_, LV_OBJ_FLAG_HIDDEN);

    mute_label_ = lv_label_create(screen);
    lv_label_set_text(mute_label_, "");
    lv_obj_add_flag(mute_label_, LV_OBJ_FLAG_HIDDEN);

    low_battery_popup_ = lv_obj_create(screen);
    lv_obj_set_scrollbar_mode(low_battery_popup_, LV_SCROLLBAR_MODE_OFF);
    lv_obj_set_size(low_battery_popup_, 320, 42);
    lv_obj_align(low_battery_popup_, LV_ALIGN_BOTTOM_MID, 0, -10);
    lv_obj_set_style_bg_color(low_battery_popup_, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(low_battery_popup_, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(low_battery_popup_, 2, 0);
    lv_obj_set_style_border_color(low_battery_popup_, lv_color_black(), 0);
    lv_obj_set_style_radius(low_battery_popup_, 12, 0);
    lv_obj_set_style_pad_all(low_battery_popup_, 6, 0);
    lv_obj_remove_flag(low_battery_popup_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(low_battery_popup_, LV_OBJ_FLAG_HIDDEN);

    low_battery_label_ = lv_label_create(low_battery_popup_);
    lv_obj_set_style_text_font(low_battery_label_, font_ai, 0);
    lv_obj_set_style_text_color(low_battery_label_, lv_color_black(), 0);
    lv_obj_set_style_text_align(low_battery_label_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(low_battery_label_, 300);
    lv_obj_center(low_battery_label_);
    lv_label_set_text(low_battery_label_, "电量低，请尽快充电");

    emoji_label_ = lv_label_create(screen);
    lv_label_set_text(emoji_label_, "");
    lv_obj_add_flag(emoji_label_, LV_OBJ_FLAG_HIDDEN);

    emoji_image_ = lv_image_create(screen);
    lv_obj_add_flag(emoji_image_, LV_OBJ_FLAG_HIDDEN);

    chat_message_label_ = chat_status_label_;

    ESP_LOGI(TAG, "星语伴侣 RLCD UI 创建完成");
}
