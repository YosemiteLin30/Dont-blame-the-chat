# Don't Blame the Chat, Blame the Game

2D 像素風恐怖解謎遊戲：實況主被困在 3x3 的黑暗迷宮，要找齊 3 個數字、推出出口密碼；Twitch 聊天室是敵人，會鎖房間、洗牌房間、熄燈來搗蛋。

## 執行
```
pip install -r requirements.txt
python main.py --sim-chat            # 沒有 Twitch 也能玩，用假聊天室測試
python main.py --channel 你的頻道     # 讀取真正的 Twitch 聊天室
```
- 控制面板：http://127.0.0.1:8000/ （即時狀態、冷卻時間、事件紀錄，也能用按鈕手動觸發事件）。
- 讀 Twitch 聊天需要環境變數 `TWITCH_TOKEN=oauth:xxxx`（用你的帳號或機器人帳號產生的 token）。沒設定時遊戲和面板仍可正常使用。
- 選項：`--host --port --seed --db`。

## 操作
WASD 移動、滑鼠瞄準手電筒（約 60 度）、E 撿數字／在出口輸入密碼、R 重新開始、Esc 離開。

## 規則
- 3 個 Angel 在黑暗中用「房間圖的最短路徑」追你；被手電筒照到（且沒有牆擋住）就凍結。
- 數字藏在不同房間的角落，靠近按 E 撿起。密碼 = 數字依「撿到的房間編號」由小到大排序，同房間依撿取順序（例：房間 8 撿 2、房間 4 撿 5 和 9 → 592）。
- 撿齊 3 個數字後：Angel 加速 30%，手電筒光束變窄。到出口按 E 輸入密碼，輸入正確會進入「最後停電」，手電筒關閉、Angel 自由移動，要在被抓到前跑到出口。
- 聊天室指令（全體共用冷卻）：

| 指令 | 效果 | 冷卻 |
|---|---|---|
| `!lock` / `!lock 4` | 封鎖一個房間 2 秒 | 10 秒 |
| `!shuffle` | 洗牌各房間（物件和 Angel 跟著房間移動） | 20 秒 |
| `!blackout` | 手電筒關閉 3 秒 | 5 秒 |
| `!chaos` | 熄燈加洗牌 | 30 秒 |
| `!speed` | Angel 加速 30%，持續 8 秒 | 20 秒 |

每位觀眾另有 3 秒個人冷卻，避免洗版。數值都在 `data/config.json`，房間版面在 `data/layout.json`。

文件沒有明確規定的地方，我這樣決定（可在程式或設定中修改）：洗牌不會移動玩家所在的房間；`!lock` 不會鎖玩家所在的房間，也不會鎖在玩家身旁的門口；熄燈 3 秒；`!speed` 持續 8 秒；最後停電階段聊天室仍可用 lock／shuffle／speed。

## 程式結構
| 檔案 | 內容 |
|---|---|
| `game/world.py` | 遊戲規則（玩家、手電筒、數字、密碼、勝敗），不含畫面與網路 |
| `game/angel.py` | Angel 狀態機：HUNT / FROZEN / BLOCKED |
| `game/pathfinding.py` | 房間圖的 BFS 最短路徑 |
| `game/events.py` | 聊天事件、冷卻、持續時間 |
| `game/render.py` | Pygame 畫面與 HUD |
| `game/db.py` | SQLite：每局紀錄與事件紀錄 |
| `chat/` | 指令解析、TwitchIO 機器人、假聊天室 |
| `server/` | FastAPI 控制面板（WebSockets）、與遊戲迴圈的橋接 |
| `data/` | `config.json`、`layout.json`、`sessions.db`（執行後產生） |
| `main.py` | 啟動遊戲、面板與機器人 |

## 測試
```
python -m pytest
```
25 個測試：幾何與尋路、Angel 凍結／追擊／穿門／被鎖、密碼排序、撿數字與輸入密碼、勝敗、各事件與冷卻、資料庫、聊天解析、面板 API 與 WebSocket、畫面各階段繪製。

## 已知限制
- 真正連線 Twitch 的部分（TwitchIO 機器人）沒有在真實頻道上測過，只測了建立機器人和指令處理；請先用自己的頻道試跑。
- 機器人只讀聊天室，不會在聊天室回覆指令結果（結果顯示在遊戲畫面和控制面板）。
- 畫面是程式繪製的簡易像素圖，沒有使用美術素材。
