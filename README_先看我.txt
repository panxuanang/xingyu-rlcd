星语伴侣 · Waveshare ESP32-S3 RLCD 4.2 一键在线编译包
====================================================

这个包的目标很简单：
上传到 GitHub → 点一次 Run workflow → 下载 BIN → 烧录。

已经包含的修改：
1. 400×300「星语伴侣 / STELLAR AI」黑白动漫首页。
2. 去掉首页底部功能栏。
3. 放大 AI 对话区域。
4. 加入固定黑白动漫女性形象。
5. 保留天气、Wi-Fi、电量、温湿度、备忘提醒。
6. 修复长对话：取消原来“逐像素慢慢滚动 + 滚到底后无限重播”。
   新方式是：短回答正常从顶部显示；超长/流式回答直接显示最新一屏，
   不做连续滚动动画，因此更适合 RLCD，也会少很多无意义刷新。

你不需要安装 ESP-IDF。
GitHub 会自动下载完整的小智源码，并用官方 ESP-IDF Docker 环境在线编译。

【第一次使用，只做下面几步】

1. 解压这个 ZIP。
2. 登录 github.com，新建一个空仓库，例如：xingyu-rlcd。
3. 在新仓库点 Add file → Upload files。
4. 把解压后的所有内容上传进去（一定要包含 .github、overlay、scripts 三个文件夹）。
5. 点绿色 Commit changes。
6. 点仓库顶部 Actions。
7. 左侧点 “Build Xingyu RLCD BIN”。
8. 右侧点 “Run workflow” → 再点绿色 “Run workflow”。
9. 等这次任务变成绿色成功。
10. 点进去，在页面最下面 Artifacts 下载 “Xingyu_RLCD_4.2_BIN”。
11. 解压下载的 Artifact，里面就是：

    Xingyu_RLCD_4.2_merged.bin

这就是你要烧录的完整 BIN。

注意：
- 这是 Waveshare ESP32-S3 RLCD 4.2 专用构建。
- GitHub 在线编译时只构建这个板子，不会把其它板子一起编译。
- 如果 Actions 变红，不要自己猜。把红色报错页面截图或复制最后 30~50 行发给我，
  我会继续把构建包修到能出 BIN。
