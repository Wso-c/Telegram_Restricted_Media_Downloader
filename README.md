<p align="center">
  <img width="15%" align="center" src="https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/logo.png" alt="logo">
</p>
  <h1 align="center">
  Telegram_Restricted_Media_Downloader
</h1>
<p align="center">
</p>
<p align="center">
  A telegram downloader on Windows and Linux platform based on Python.
</p>
<p align="center">
  <a style="text-decoration:none">
<img src="https://img.shields.io/badge/Python-3.13.2-blue.svg?color=00B16A" alt="Python 3.13.2"/>
  </a>
  <a style="text-decoration:none">
<img src="https://img.shields.io/badge/pyrogram@kurigram-2.2.26-blue.svg?color=00B16A" alt="pyrogram@kurigram 2.2.26"/>
  </a>
  <a style="text-decoration:none">
<img src="https://img.shields.io/badge/Platform-Windows & Linux%20-blue?color=00B16A" alt="Platform Windows & Linux"/>
  </a>
<a href="https://deepwiki.com/Gentlesprite/Telegram_Restricted_Media_Downloader"><img alt="DeepWiki" src="https://img.shields.io/badge/DeepWiki-Documentation-blue?color=00B16A">
  </a>
</p>


> [!NOTE]
> 由於本專案提供的 Linux 版本或未能相容較舊的 Linux 系統。\
> 如 Linux 版本無法執行，請參閱[_「3.0.在生產環境中執行（Linux 使用者）」_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#%E5%AF%B9%E4%BA%8Elinux%E7%94%A8%E6%88%B7-2)或[_「6.0.透過 Docker 執行」_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#60%E9%80%9A%E8%BF%87docker%E8%BF%90%E8%A1%8C)。\
> 如果你**遇到任何問題**，請先仔細**閱讀**:[_“常見問題及解決方案彙總”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/wiki)。\
> 如未找到解決方案，請加入群組或私訊查詢。

# 免責聲明

本專案以`GNU GPL-3.0`協議開源發佈。

**所有使用本軟件的行為及其後果均由使用者自行承擔全部法律責任**，開發者不對任何使用行為及其後果負責。

------

*本專案按“原樣”提供，不附帶任何明示或暗示的保證。*

|      作者       |       [Gentlesprite](https://github.com/Gentlesprite)        |
| :-------------: | :----------------------------------------------------------: |
| YouTube影片教學 |   [點擊觀看](https://www.youtube.com/watch?v=ucwKJu-MrBw)    |
| Telegram 群組  |          [點擊加入](https://t.me/+6KKA-buFaixmNTE1)          |

# 1.0.下載網址

|      平台      |                           下載網址                           |    備註    |
| :------------: | :----------------------------------------------------------: | :--------: |
|     Github     | [點擊前往](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/releases) |  &ndash;   |
|     Gitee      | [點擊前往](https://gitee.com/Gentlesprite/Telegram_Restricted_Media_Downloader/releases) | 僅發佈源碼 |
|     藍奏雲     |         [點擊前往](https://wwgr.lanzn.com/b0fopovuf)         | 密碼:ceze  |
| Telegram 群組 |          [點擊加入](https://t.me/+6KKA-buFaixmNTE1)          |   群組檔案   |

## 1.1.推薦終端機（選看）
<details>
<summary><strong>點擊展開</strong></summary>

1. _對於Windows11用戶_，`Windows Terminal`預設**已經安裝好**，可**跳過**下載的步驟，直接前往第3步（將`Windows Terminal`設為**預設終端機**）。

2. _對於Windows10用戶_，推薦使用`Windows Terminal`作為**預設終端機**，僅作為推薦安裝，無論安裝與否**不會影響本軟件的使用**，`Windows Terminal`能提供更出色的顯示、互動、體驗效果，以及避免出現**文字顯示**亂碼。

   `Windows Terminal`下載網址如下表：

   |   平台   |                           下載網址                           |
   | :------: | :----------------------------------------------------------: |
   | 微軟商店 | [點擊前往](https://apps.microsoft.com/detail/9n0dx20hk701?launch=true&mode=full&hl=zh-cn&gl=cn&ocid=bingwebsearch) |
   |  Github  |  [點擊前往](https://github.com/microsoft/terminal/releases)  |

3. 完成下載後`win+r`輸入`wt`按 Enter開啟，然後將`Windows Terminal`設為**預設終端機**再啟動軟件，教程如下：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/1_1_1.png)

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/1_1_2.png)

</details>

# 2.0.快速開始

## 2.1.申請電報API

1. 前往網站:**https://my.telegram.org/auth**

   

2. 填寫**自己綁定**`Telegram`電報的**手機號**注意手機號格式先要+地區再寫入電話號碼例如`+12223334455`，`+1`為地區，`222333445`為你綁定`Telegram`的**手機號**，填寫後點擊`Next`。

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_1_1.png)

   

3. 開啟你的`Telegram`用戶端，此時會收到來自`Telegram`帳號的訊息，將上面的驗證碼填入`Confirmation code`框中，然後點擊`Sign in`。

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_1_2.png)

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_1_3.png)

   

4. 點擊`API development tools`按照提示填入即可。

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_1_4.png)

   

5. 申請成功會得到一個`api_hash`和`api_id`儲存下載，**切記不要泄露給任何人！**

## 2.2.電報機械人`bot_token`申請及使用教程（選看）
> [!NOTE]
> 如果設定了機械人，只要**保持軟件執行**，就能實現**多端發送下載命令**並且**隨時進行下載**。\
> 故可以將軟件部署在伺服器上，無論是Windows還是Linux平台。\
> Windows平台可直接使用[releases](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/releases)裏發佈的二進制檔案放在伺服器執行。\
> Linux平台的部署教程請**閱讀**:[_“3.0.在生產環境中執行（對於Linux用戶）”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#%E5%AF%B9%E4%BA%8Elinux%E7%94%A8%E6%88%B7)。


<details>
<summary><strong>點擊展開</strong></summary>

### 2.2.1.申請教程

1. 前往網站：https://t.me/BotFather

2. 開啟後會**提示**"要開啟 Telegram Desktop 嗎？"此時**點擊**"開啟Telegram Desktop"如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_1.png)

   如果沒有這個彈出視窗，說明電腦沒有安裝**Telegram用戶端**，安裝後再重試即可。

3. **點擊開始**，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_2.png)

4. 然後在目前**對話框**中輸入`/newbot`後按 Enter，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_3.png)

   它會回覆你`"Alright, a new bot. How are we going to call it? Please choose a name for your bot."`意思是給機械人取一個名字，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_4.png)

5. 這個名字是顯示名稱（display name），並不是唯一識別碼，隨便設定一下即可，之後可以通過 `/setname`命令進行修改。

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_5.png)

6. 接着設定機械人的**唯一名稱**。字串必須 以`bot`結尾，比如 `HelloWorld_bot` 或 `HelloWorldbot` 都是合法的。如果設定的名字已經被佔用需要重新設定。如設定成了 `trmd_bot`但是這個名字已經有人使用了，此時會提示`"Sorry, this username is already taken. Please try something different."`意思是已經被使用了，需要擬定一個**不重複**的，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_6.png)

   如果結果如**上圖**所示，則就代表名字**重複**了，需要**重新擬定**一個。

7. 直到提示你`"Done! Congratulations on your new bot. . ."`如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_7.png)

   如果結果如**上圖**所示，則代表`bot_token`申請成功了，箭頭指的紅框處就是你所申請的`bot_token`，**切記不要泄露給任何人！**

### 2.2.2.使用教程

1. 申請完成後，在軟件設定時詢問"是否啟用「機械人」（需要提供bot_token）？ - 「y|n」（預設n）"選擇`y`代表**需要**使用，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_8.png)

   然後在**上圖**箭頭所指處填入"2.2.1.申請教程"第7步申請的`bot_token`後按 Enter，即可設定完成。

2. 在一切設定完成，軟件啟動成功後等待提示"「機械人」啟動成功。"，就代表機械人可以使用了，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_9.png)

3. 在`Telegram`用戶端中找到與`BotFather`的對話框，找到"2.2.1.申請教程"第7步對話的位置（或者用你自己的方式找到你的機械人的對話框），如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_10.png)

   然後在**上圖**箭頭所指處即可**跳轉**到機械人對話框。

4. **點擊**開始，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_11.png)

   不出意外，會收到一條來自**機械人**發送的訊息，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_12.png)

   **如果沒收到**嘗試嘗試給機械人發送任意命令。

5. 目前機械人支援的命令用法及解釋如下表所示：

   | 命令               | 用法                                                         | 解釋                                                         |
   | :----------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
   | `/help`            | 向機械人發送發送`/help`即可。                                | 展示**可用**命令。                                           |
   | `/download`        | `/download 連結1 連結2 連結3 連結n`或`/download 頻道連結 1 100` | 分配**新的**下載任務，兩種方式可選（**指定連結下載**和**範圍下載**，具體使用方法請見下方說明）。 |
   | `/table`           | 向機械人發送`/table`即可。                                   | 在**終端機**輸出**目前**下載情況的**統計資訊**。               |
   | `/forward`         | `/forward https://t.me/A https://t.me/B 1 100 `              | 將**頻道A**的訊息轉發至**頻道B**，其中`1`代表`起始ID`，`100`代表截止`ID`。 |
   | `/exit`            | 向機械人發送`/exit`即可。                                    | **退出**軟件。                                               |
   | `/listen_download` | `/listen_download https://t.me/A https://t.me/B https://t.me/n` | **即時**監聽**頻道A**、**頻道B**和**頻道n**的**最新訊息**（影片和圖片）進行下載。 |
   | `/listen_forward`  | `/listen_forward https://t.me/A https://t.me/B`              | **即時**監聽**頻道A**的**最新訊息**（任意訊息）轉發至**頻道B**。但當**頻道A**為**私密頻道**時候無法轉發。 |
   | `/listen_info`     | 向機械人發送`/listen_info`即可。                             | 查看目前已經建立的監聽資訊。                                 |
   | `/upload`          | `/upload` `本機檔案` `目標頻道`                              | 上載**本機的檔案**到**指定頻道**。                           |
   | `/upload_r`        | `/upload_r 本機資料夾 目標頻道`                              | **遞迴**上載資料夾（**包含子資料夾**）到**指定頻道**。         |
   | `/download_chat`   | `/download_chat 頻道連結`                                    | 下載**指定頻道**並支援**通過內聯鍵盤自訂內容過濾**。       |

   其他功能：
   - （`≥v1.8.7`）轉發`影片`、`圖片`、`音訊`、`語音`、`GIF`、`檔案`、`影片筆記`、`實況圖片`類型的訊息給機械人，即可建立下載任務。
      - 此項功能不受用戶自訂下載類型限制，確保檔案即時取得。
      - 轉發的訊息將按新訊息處理，每次均生成獨立檔案命名。暫不支援重複檔案識別，請妥善管理多次轉發的相同內容。
      - 此功能僅用於便利用戶日常使用，對於無法被轉發、下載的訊息，請根據實際需求使用對應的命令。

---

### 2.2.3.命令

#### /help


---

#### 選單

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_14.png)

---

#### /download
> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.6.3` | 已全面支援下載時的斷點續傳功能（支援所有上載場景），增強了在較差網絡環境下的傳輸穩定性與可靠性。 |

   - 方式一：
     - ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_15.png)
     - 只要發送了正確的下載命令，終端機就會建立對應的下載任務，如下圖所示：
     - ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_16.png)

   - 方式二：

     - 該功能為版本`≥v1.5.1`的新增功能，用於對於**單一連結**的範圍下載，並且該方式要求指定**頻道連結**、**起始ID**與**結束ID**：

       ```bash
       # 語法格式如下：
       /download 頻道連結 起始ID 結束ID
       # 舉例：
       /download https://t.me/test 1 500
       # 代表下載https://t.me/test從訊息ID=1到結束ID=500的媒體。
       ```

---

#### /table

   需要**注意**的是，這個表格是**即時**的**狀態**，並不是**最終**下載完成的**結果**，每一次使用它都會隨着**目前**的**下載記錄**而更新。

   **連結統計表**的使用，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_17.png)

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_18.png)

   **注意**：由於早期代碼設計缺陷，**連結統計表**為後續支援的功能：

   - **連結統計表**僅會統計**所有支援的類型**，**並不會只統計**用戶**目前所選擇**的類型。

   - **連結統計表**對於**評論區媒體**的統計，會出現**總數統計錯誤**的問題，體現在**總數**為`1`，**小於**目前的**下載數**，**完成率**`>>100%`的問題（該問題已在`≥v1.5.9`修復）。

   - 當用戶**未選擇**下載**所有支援的類型**時，在**用戶所選擇的類型**下載完成後（或使用機械人發送**連結統計表**），儘管所有用戶指定類型的檔案已經下載完成，當**連結統計表**顯示`完成率`不為`100%`時，代表該連結還存在其他用戶未指定的檔案類型，但實際用戶所指定的類型已經下載完成了，是正常情況（該問題已在`≥v2.0.2`調整：在機械人設定或設定檔中被定義為跳過的下載類型與不支援的下載類型，統計時不再計入總數）。
   
   - 版本`≥v1.6.5`起已支援**匯出表格**功能，通過該命令可在執行時控制**是否**在退出後**匯出指定類型的表格**。
   
   **計數統計表**的使用，如下圖所示：
   
   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_19.png)
   
   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_20.png)
   
---

#### /forward

> **⚠️ 注意：**  
> 訊息能否轉發，在於頻道是否開啟了`限制儲存內容`功能。\
> 如果**無法轉發**，**機械人**會在**對話框**提供一個**下載按鈕**與**下載後上載按鈕（`≥v1.6.7`）**。\

> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.6.9` | `/forward`將支援過濾轉發類型。可通過`[說明頁面]`->`[設定]`->`[轉發設定]`進行修改。 |
| `≥v1.7.5` | 為確保"受限轉發"功能順利完成，在**下載後上載**過程中，建立下載任務時將**忽略設定檔中設定的下載類型限制**，此時（指"受限轉發"情況）`/forward`命令**無法按照**`[轉發設定]`過濾類型。 |
| `≥v1.8.5` | 為確保"受限轉發"功能順利完成，在**下載後上載**過程中，建立下載任務時將**忽略該連結是否被重複添加的判定**。 |

- 轉發訊息語法：
    ```bash
    /forward 頻道A 頻道B 起始ID 結束ID
    ```

- 實例：

    - 該實例代表轉發`https://t.me/test`**頻道**中從`訊息ID=1`到`結束ID=500`的訊息到 `https://t.me/test2` **頻道**。

    ```bash
    /forward https://t.me/test https://t.me/test2 1 500
    ```

- 轉發至個人收藏夾（任選一種命令即可）：

    - 方式1，使用`me`或`self`指向個人收藏夾（任選一種命令即可）：

      ```bash
      /forward https://t.me/test me 1 500
      ```

      ```bash
      /forward https://t.me/test self 1 500
      ```

    - 方式2，使用 `https://t.me/用戶名稱` ：

      - 用戶名稱即指個人帳戶資訊裏@後面那一串，需用戶提前自行設定，否則無法使用該方式。
      - 例如通過查詢個人資訊，得知目前設定的用戶名稱為`@developer`，此時指向個人的連結即為`https://t.me/developer`。

      ```bash
      /forward https://t.me/test https://t.me/developer 1 500
      ```

    - 無論使用方式1或方式2，都代表轉發 `https://t.me/test`  **頻道 **中從`訊息ID=1`到結束`ID=500`的訊息到**個人收藏夾**。

- 轉發個人收藏夾的內容至任意頻道：

   - 方式1：

      ```bash
      /forward me https://t.me/test 1 500
      ```

   - 方式2：

      ```bash
      /forward https://t.me/developer me 1 500
      ```

   - 無論使用方式1或方式2，都代表轉發**個人收藏夾**中從`訊息ID=1`到結束`ID=500`的訊息到`https://t.me/test` **頻道**。


---

#### /exit

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_2_21.png)

---

#### /listen_download

- `/listen_download`監聽下載用於，即時監聽該連結的最新訊息進行下載。
   - 在用戶發送了正確的監聽命令後，會收到機械人的成功提示。
   - 當被監聽的頻道有可下載的內容時，就會自動發送命令下載。

##### 註冊監聽下載

```bash
/listen_download https://t.me/A
```

##### 註銷監聽下載

###### 註銷方法

_再次向機械人發送建立監聽時的命令，機械人將會提供給用戶一個用於註銷監聽的內聯鍵盤，點擊確認即可。_

**_與此同時，也可通過`網頁面板`的`監聽`版塊提供的按鈕註銷監聽下載（≥v2.0.2）。_**

```bash
/listen_download https://t.me/A
```

##### 註冊多個監聽下載

```bash
/listen_download https://t.me/A https://t.me/B https://t.me/n
```

##### 註銷多個監聽下載

```bash
/listen_download https://t.me/A https://t.me/B https://t.me/n
```

---

#### /listen_forward

> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.6.7` | 當檢測到"受限轉發"時，自動採用"下載後上載"的方式（預設**開啟**）。當**下載並完成上載**後，可選擇**是否刪除本機檔案**（預設**關閉**）。並且可通過`[說明頁面]`->`[設定]`->`[上載設定]`進行修改。 |
| `≥v1.6.9` | `/listen_forward`將支援過濾轉發類型。可通過`[說明頁面]`->`[設定]`->`[轉發設定]`進行修改。 |
| `≥v1.7.5` | 為確保"受限轉發"功能順利完成，在**下載後上載**過程中，建立下載任務時將**忽略設定檔中設定的下載類型限制**。 |
| `≥v1.8.5` | 為確保"受限轉發"功能順利完成，在**下載後上載**過程中，建立下載任務時將**忽略該連結是否被重複添加的判定**。 |

- `/listen_forward`監聽轉發用於，即時監聽該連結的最新訊息。
   - 與`/forward`命令一樣，訊息能否轉發，在於頻道是否開啟了`限制儲存內容`功能。
   - 但在`≥v1.6.7`起可以通過下載再上載的方式進行"轉發"。
   - 在用戶發送了正確的監聽命令後，會收到機械人的成功提示。
   - 當被監聽的頻道有**任何**新內容時，就會自動轉發至用戶所指定的頻道。

##### 監聽行為說明

- **頻道獨佔原則：**
   - 每個頻道**同一時間**只能激活一種監聽模式（下載或轉發）。
   - 對於`/listen_forward`命令，"同一頻道"特指**被監聽**的源頻道。
   - 轉發目標頻道**不受此限制**，仍可通過`/listen_download`建立下載任務。
- **操作限制：**
   - 當`頻道A`正在監聽轉發`頻道B`時：
      - 可以**同時**在`頻道B`設定監聽下載。
      - 但`頻道B`的監聽下載，不會響應來自`頻道A`的監聽轉發。
- **監聽切換流程：**
   - 必須先通過**同一命令**（註冊監聽時的命令）來取消現有監聽。
   - 然後才能建立**新的監聽**事件。

##### 註冊監聽轉發

```bash
/listen_forward https://t.me/A https://t.me/B
```

##### 註銷監聽轉發

###### 註銷方法

_再次向機械人發送建立監聽時的命令，機械人將會提供給用戶一個用於註銷監聽的內聯鍵盤，點擊確認即可。_

**_與此同時，也可通過`網頁面板`的`監聽`版塊提供的按鈕註銷監聽轉發（≥v2.0.2）。_**

```bash
/listen_forward https://t.me/A https://t.me/B
```

---

#### /listen_info

- `/listen_info`用於查看**目前**已經建立的**監聽資訊**，**直接發送**即可：

    ```bash
    /listen_info
    ```

---

#### /upload
> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.7.9` | 已全面支援上載時的斷點續傳功能（支援所有上載場景），增強了在較差網絡環境下的傳輸穩定性與可靠性。 |
| `≥v1.8.4` | `/upload` 命令支援`me`、`self` 作為目標頻道的參數（`me`、`self` 作為目標頻道參時，代表指向個人收藏夾`Saved Messages`）。 |

- `/upload`用於上載本機的檔案到指定頻道。
  
   - 支援上載資料夾（當指定路徑為資料夾時並且版本需≥v1.7.1）。
   - _當指定的路徑為**資料夾**時，將會上載指定資料夾下**所有**的檔案。_
- 上載檔案語法：
  
    ```bash
   /upload 本機檔案（夾） 目標頻道
   ```
##### 注意事項

`Telegram` 對上載的**單個檔案**大小設有**明確限制**：

- **普通用戶**：**單個檔案**最大上載大小為`2000 MiB`（約 2 GB）。
- **會員用戶（Telegram Premium）**：**單個檔案**最大上載大小為`4000 MiB`（約 4 GB）。

##### 對於Windows用戶
###### 上載一個檔案
```bash
/upload C:\files\video.mp4 https://t.me/test
```
###### 上載一個資料夾
_版本需要`≥v1.7.1`。_
```bash
/upload C:\files https://t.me/test
```
##### 對於Linux用戶
###### 上載一個檔案
```
/upload /home/username/files/video.mp4 https://t.me/test
```
###### 上載一個資料夾
_版本需要`≥v1.7.1`。_
```
/upload /home/username/files https://t.me/test
```

---

#### /upload_r
> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.8.4` | `/upload_r`命令支援`me`、`self`作為目標頻道的參數（`me`、`self`作為目標頻道參時，代表指向個人收藏夾`Saved Messages`）。 |

- `/upload_r`命令是`/upload`命令的擴展版本，專為**批量檔案上載**場景設計，支援遞迴處理目錄結構，與`/upload`不同的是：

  - `/upload_r`命令接收**資料夾路徑**作為其第二個參數，自動**遍歷該目錄**及其**所有子目錄**中的檔案。

    ```bash
    /uploadr C:\files https://t.me/test
    ```

  - 當**第二個參數**為**檔案路徑**時，自動切換為 `/upload`的單檔案上載模式。

    ```bash
    /uploadr C:\files\video.mp4 https://t.me/test
    ```

    ```bash
    /upload C:\files\video.mp4 https://t.me/test
    ```

    _以上兩個命令在功能上完全等效，系統會自動識別檔案類型並採用相應的上載策略。_

---

#### /download_chat

- `/download_chat`下載指定頻道。

   - 與`/download`不同的是：`/download_chat`支援通過機械人發送的內聯鍵盤進行自訂內容過濾。
   - 該命令支援下載無法複製具體請求連結的對話。
   - 使用該命令後，**需要通過操作機械人回覆中的內聯鍵盤**，來設定過濾器、執行任務或取消任務。
   - 需要注意的是，在上一個`/download_chat`命令任務未執行或取消前，無法發起新的`/download_chat`命令來建立下載任務。
   - 自版本`≥v1.7.5`起，`/download_chat`命令建立的下載任務過濾條件將完全遵循用戶在內聯鍵盤中的設定，意味着該命令不會遵循設定檔中的任何規則（例如設定檔中的下載檔案類型設定）。
   
- 目前支援的過濾方式：

|  過濾方式  |                       預設值                        |
| :--------: |:------------------------------------------------:|
|  日期範圍  |           `第一條訊息的發送日期`～`最後的一條訊息的發生日期`            |
|  檔案類型  | `影片`、`圖片`、`檔案`、`音訊`、`語音`、`動畫（GIF）`、`影片筆記`、`實況照片` |
| 匹配關鍵詞 |                     &ndash;                      |
| 包含評論區 |                       `關`                        |

- 下載指定頻道語法：

   ```bash
   /download_chat 頻道連結
   ```

   - 發送命令後，可**根據個人需求**設定過濾器（可選）。

   - 在設定完成後，必須**手動點擊**"執行任務"或"取消任務"以繼續或終止流程，否則該命令將**始終處於等待狀態，並阻塞新的`/download_chat`命令。**

- 下載用戶與機械人的對話媒體：

    用戶與機械人的對話無法複製具體的請求連結，因此該方法用於解決某些用戶與機械人對話中禁止用戶進行轉發、下載的情況。

    - 首先要取得機械人用戶名稱，在對話方塊中點擊機械人名稱查看其用戶名稱，此處假設機械人名稱為`@developer_bot`。

    - 拼接機械人的請求連結為`https://t.me/developer_bot`。

        ```bash
        /download_chat https://t.me/developer_bot
        ```

- 下載個人收藏夾（任選一種命令即可）：

    - 方式1（任選一種命令即可）：

      ```bash
      /download_chat me
      ```

      ```bash
      /download_chat self
      ```

    - 方式2：

      - 首先要取得用戶名稱，此處假設用戶名稱已設定，個人資訊中查看用戶名稱為`@developer`。
      - 拼接個人收藏夾的請求連結為`https://t.me/developer`。

      ```bash
      /download_chat https://t.me/developer
      ```

- 自版本`≥v1.8.8`起，`/download_chat`命令新增通過匹配關鍵詞下載，匹配關鍵詞說明：
    - 該命令會根據訊息的`text（文字）`和`caption（標題）`資訊，篩選並下載包含所設定關鍵詞的相關對話內容。
    - 在使用該命令後點擊[`🔑設定匹配關鍵詞`]此時，機械人將進入接收關鍵詞模式。
    - 關鍵詞可以為一個或多個，當關鍵詞為多個時，以空格分隔，例如：
    
      `我的最愛`
    
      `學習 資料 健康 營養`

    - 用戶再次發送已添加的關鍵詞時，機械人會提供一個[`⌨️內聯鍵盤`]按鈕用於[`🗑️移除`]或[`👁️‍🗨️忽略`]該關鍵詞。
    - 同一時段內發送多個相同的已添加關鍵詞，只會對第一個觸發移除選項，後續重複內容不會重複觸發。
    - 在[`🔑設定匹配關鍵詞`]介面：
       - 點擊[`✅確認關鍵詞`]時，將會添加所有設定的關鍵詞。
       - 點擊[`❌取消`]時，將會清空所有設定的關鍵詞。
       - 點擊[`🔙返回`]時，不做任何操作，僅返回至主頁面。
- 包括評論區設定說明：
   - 評論區開關：
     - 預設為關閉狀態。
     - 開啟時，按鈕狀態為[`✅包含評論區`]，匹配到的訊息，存在評論區模塊時，進一步匹配評論區。
     - 關閉時，按鈕狀態為[`❌包含評論區`]，匹配到的訊息，存在評論區模塊時，忽略評論區內容。
   - 評論區功能適用性：
     - 平台部分頻道在訊息下方設有評論區模塊，該功能為可選擴展項。用戶需基於個人實際需求，自行判斷是否需同步取得評論區內容。
     評論區匹配與過濾規則：
     - 開啟包含評論區選項後，即便訊息因`媒體類型`被過濾而未下載，但**只要該訊息存在評論區**，其評論同樣會被取得（`≥v2.0.8`）。
     - **評論區的過濾條件僅遵循本次任務中用戶指定的`媒體類型`作為過濾條件，其餘過濾條件將被忽略（例如日期）。**
   - 任務處理時效性：
     - 開啟包含評論區選項後，需對所匹配到的訊息的評論區進行讀取，訊息過多時，任務建立至完成的時間可能相應延長，需耐心等待。
</details>

## 2.3.設定檔說明

### 用戶設定檔

> [!NOTE]
> 用戶設定檔通常無需自行設定，此處旨在介紹全局設定檔中各參數的含義。\
> 用戶設定檔會在軟件啟動時自動在軟件目錄下生成`config.yaml`檔案，並詳細地引導用戶設定參數。\
> **手動編輯**`config.yaml`對設定進行修改時，請仔細閱讀下面內容理解各參數含義。\
> 需注意設定檔使用的引號、冒號均為半角，冒號後需有一個空格。\

```yaml
api_hash: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
api_id: 'xxxxxxxx'
bot_token: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
download_type:
  - video
  - photo
  - document
  - audio
  - voice
  - animation
  - video_note
  - live_photo
is_shutdown: true
links: D:\path\where\your\link\files\save\content.txt
max_retries:
  download: 5
  upload: 3
max_tasks:
  download: 3
  upload: 3
proxy:
  enable_proxy: true
  hostname: 127.0.0.1
  scheme: socks5
  port: 10808
  username: null
  password: null
save_directory: F:\directory\media\where\you\save
session_directory: F:\directory\session\where\you\save
temp_directory: F:\directory\temp\where\you\save
```

#### 參數說明

| 參數 | 說明                                                                                                                                                                                                                                          |
| --- |---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `api_hash` | 申請的`api_hash`（Telegram API 憑據）。                                                                                                                                                                                                             |
| `api_id` | 申請的`api_id`（Telegram API 憑據，需加引號）。                                                                                                                                                                                                          |
| `bot_token` | 機械人令牌（選填）；不填則無法使用機械人功能，可前往[BotFather](https://t.me/BotFather)免費申請。                                                                                                                                                                          |
| `download_type` | 需要下載的媒體類型，詳見`download_type`參數支援下載的媒體類型表。                                                                                                                                                                                                      |
| `is_shutdown` | 下載完成後是否自動關機，支援`true`、`false`。                                                                                                                                                                                                               |
| `links` | 連結地址文字檔案路徑（一個連結一行，不要加引號，執行前準備好）。                                                                                                                                                                                                            |
| `max_retries` | 任務重試次數，含`download`（下載任務重試次數）與`upload`（上載任務重試次數）。                                                                                                                                                                                            |
| `max_tasks` | 最大併發任務數，含`download`與`upload`。                                                                                                                                                                                                               |
| `proxy` | 代理設定，子字段詳見`proxy`參數設定項表；不使用代理時請將`enable_proxy`設為`false`（注意鍵值間冒號後需保留空格，否則`YAML`解析報錯）。 |
| `save_directory` | 下載媒體儲存目錄（支援通配符）。                                                                                                                                                                                                                            |
| `session_directory` | 會話儲存目錄（支援通配符）。                                                                                                                                                                                                                              |
| `temp_directory` | 快取儲存目錄（支援通配符）。                                                                                                                                                                                                                              |

##### `download_type`參數支援下載的媒體類型

| 下載類型        | 說明                         |
| --------------- |----------------------------|
| `video`         | 影片。                        |
| `photo`         | 圖片。                        |
| `document`      | 檔案。                        |
| `audio`         | 音訊。                        |
| `voice`         | 語音。                        |
| `animation`     | 動畫（GIF）。                   |
| `video_note`    | 影片筆記。                      |
| `live_photo`    | 實況照片（未指定且`photo`存在時視為`photo`）。 |

##### `proxy`參數設定項

| 設定項       | 說明                                       |
| ------------ | ------------------------------------------ |
| `enable_proxy` | 是否啟用代理，支援`true`、`false`。          |
| `scheme`      | 代理協議，如`socks5`、`http`。               |
| `hostname`    | 代理伺服器`IP`或域名。                       |
| `port`        | 代理伺服器連接埠。                             |
| `username`    | 代理認證用戶名稱（選填）。                     |
| `password`    | 代理認證密碼（選填）。                       |

### 通配符說明

自版本`≥v1.7.4`起，`save_directory`參數將支援通配符，通配符允許用戶動態生成儲存路徑。系統會在下載時自動將通配符替換為對應的實際值，實現按規則自動分類儲存。

- 目前`save_directory`支援的通配符如下表所示：
  
|      通配符      |             意義             |
|:-------------:|:--------------------------:|
|  `%CHAT_ID%`  |     以實際`頻道ID`作為指定路徑填充。     |
| `%CHAT_NAME%` | 以實際`頻道名`作為指定路徑填充（≥v1.9.6）。 |
| `%MIME_TYPE%` |     以實際`檔案類型`作為指定路徑填充。     |

- 用法示例1：

  ```bash
  F:\directory\media\%CHAT_ID%
  ```

- 用法示例2（≥v1.9.6）：

  ```bash
  F:\directory\media\%CHAT_NAME%
  ```
- 用法示例3：

  ```bash
  F:\directory\media\%MIME_TYPE%
  ```

- 用法示例4：

  ```bash
  F:\directory\media\%CHAT_NAME%\%CHAT_ID%\%MIME_TYPE%
  ```

### 全局設定檔

> [!NOTE]
> 全局設定檔通常無需自行設定，此處旨在介紹全局設定檔中各參數的含義。\
> 部分參數支援通過機械人設定進行修改。

```yaml
console_log_level: WARNING
export_table:
  count: false
  link: false
file_log_level: INFO
forward_type:
  animation: true
  audio: true
  document: true
  photo: true
  text: true
  video: true
  voice: true
  video_note: true
  live_photo: true
notice: false
upload:
  delete: false
  download_upload: true
```

#### 參數說明

| 參數 | 說明                                                                    |
| --- |-----------------------------------------------------------------------|
| `console_log_level` | 終端機顯示的最低日誌級別（如`WARNING`）。                                              |
| `export_table` | 執行結束時是否匯出統計表，含`count`（下載計數統計表）與`link`（下載連結統計表）。                       |
| `file_log_level` | `TRMD_LOG.log`檔案中記錄的最低日誌級別（如`INFO`）。                                  |
| `forward_type` | 控制`/listen_forward`與`/forward`命令可轉發的檔案類型，詳見`forward_type`參數支援轉發的媒體類型。 |
| `notice` | 機械人啟動時是否發送啟動通知。                                                       |
| `upload` | 受限內容處理，含`delete`（下載上載完成後是否刪除本機檔案）與`download_upload`（是否下載後上載到指定轉發頻道）。  |

##### `forward_type`參數支援轉發的媒體類型

| 下載類型         | 說明                             |
|--------------|--------------------------------|
| `text`       | 文字。                            |
| `video`      | 影片。                            |
| `photo`      | 圖片。                            |
| `document`   | 檔案。                            |
| `audio`      | 音訊。                            |
| `voice`      | 語音。                            |
| `animation`  | 動畫（GIF）。                       |
| `video_note` | 影片筆記。                          |
| `live_photo` | 實況照片（未指定且`photo`存在時視為`photo`）。 |

### 全局設定檔存放路徑
#### 對於Windows用戶
  ```bash
  %APPDATA%/TRMD/.CONFIG.yaml
  ```
#### 對於Linux用戶
  ```bash
  ~/.config/TRMD/.CONFIG.yaml
  ```

## 2.4.使用注意事項
<details>
<summary><strong>點擊展開</strong></summary>

### 連結取得方法

對想要儲存的媒體檔案點擊**滑鼠右鍵**然後選擇**複製訊息直鏈**，如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_4_1.png)

---

### links參數的文字內容具體寫法

如下圖所示，即一行代表一個連結：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_4_2.png)

---

### 常見的links參數的文字內容的錯誤寫法

如下圖所示：

   ![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_4_3.png)

---

### 關於私密頻道連結的下載行為

- 要求目前所登入的`Telegram`帳號，在這個私密頻道中，否則會報錯無法下載。
- 這是`Telegram`伺服器端設計所決定的，任何下載器都無法越界。

---

### 重複連結問題說明

#### 問題描述

- 如上圖所示，在提交的下載任務中，存在多個**前綴相同但參數不同**的連結（如`?comment`、`?single`或`?single&comment`）。

#### 問題原因

- 當連結包含`?comment`參數時，會自動下載**原始訊息及其評論區內容**。
- 如果同時提交**相同前綴但無`?comment`的連結**，會導致**同一資源被重複添加**至下載佇列。
- 若前一次任務尚未完成，重複提交相同資源會觸發**任務衝突**，進而引發下載異常。

#### 解決方案

- **`≥v2.0.8`已針對重複連結導致的資源競爭問題進行自動處理。**
- **僅需提交一個完整連結**（如帶`?comment`的版本），系統會自動處理**原始內容及評論區**，無需額外提交無參數版本。
- **避免重複提交相同資源**，確保每條連結的`t.me/c/<頻道>/<訊息ID>`部分唯一，防止任務冗餘。
- 由於這些連結的**頻道名**和**訊息ID**完全一致，實際上指向的是**同一資源**的不同表現形式。
- 但請注意以下參數的功能差異：
  - `?comment`用於標識是否下載**評論區**內容。
  - `?single`用於在**媒體組**中指定僅下載該訊息ID對應的單個資源。
  - `?single&comment`用於指定僅下載評論區中該訊息ID所對應的內容。

---

### `Telegram`字段解釋

|                字段                 |                     解釋                      |
| :---------------------------------: | :-------------------------------------------: |
|             `?comment`              |              **評論區**的連結。               |
|              `?single`              |               **單獨**的連結。                |
|          `?single&comment`          |         **評論區**中**單獨**的連結。          |
|                `/c`                 |             **私密**頻道的連結。              |
|     `https://t.me/TEST/111/666`     |        頻道`TEST`**話題**`111`的連結。        |
| `https://t.me/c/1111111111/333/666` | **私密**頻道`1111111111`**話題**`333`的連結。 |

#### 連結解釋說明

##### `Telegram`連結組成

|   頻道類型   |                     連結組成                      |
| :----------: | :-----------------------------------------------: |
|   正常頻道   |           `https://t.me/頻道名/訊息ID`            |
|   私密頻道   |    `https://t.me/c/頻道名(10位純數字)/訊息ID`     |
|   話題頻道   |        `https://t.me/頻道名/話題ID/訊息ID`        |
| 私密話題頻道 | `https://t.me/c/頻道名(10位純數字)/話題ID/訊息ID` |

##### `Telegram`連結所有連結格式

"所有"指的是如果有**合併發送為一組**的檔案，則給定一個連結，所有**合併發送的檔案**會被全部下載。

"媒體"指的是用戶在`config.yaml`檔案中，通過`download_type`參數所設定的所需下載類型的媒體。

| 連結                                       | 實際頻道名 | 訊息ID | 解釋                                           |
|:----------------------------------------:| :----: |:----:|:--------------------------------------------:|
| `https://t.me/TEST/111`                  | `TEST` | `111` | 下載該連結的**所有媒體**。                       |
| `https://t.me/TEST/111?single`           | `TEST` | `111` | 下載該連結的**對應的一個媒體**。                       |
| `https://t.me/TEST/111?comment=666`      | `TEST` | `111` | 下載該連結的**所有媒體**的同時，下載該連結下方**評論區裏所有的媒體（前提該連結存在評論區，否則視為`https://t.me/TEST/111`處理）。** |
| `https://t.me/TEST/111?single&comment=666` | `TEST` | `111` | 下載該連結下方的**評論區**的**對應的一個媒體。** |
| `https://t.me/c/1111111111/666`          | `-1001111111111` | `666` | 下載該**私密頻道**連結的**所有**媒體。 |
| `https://t.me/TEST/111/666` | `TEST` | `666` | 下載該**話題**連結的**所有**媒體。 |
| `https://t.me/c/1111111111/333/666` | `-1001111111111` | `666` | 下載該**私密話題**連結的所有媒體。 |

---

### 如何下載評論區的檔案

#### 複製的連結時，帶`?comment`字段

通常在評論區複製任意一條訊息連結即可。

---

### 評論區連結的下載行為規則的說明

#### 標準連結（無`?comment`參數）

- 僅下載**訊息正文內容**（即頻道/群組中直接發佈的原始訊息）。
- **不包含評論區內容**，即使原訊息存在評論，也不會被納入下載任務。

#### 帶`?comment`參數的連結

- 下載**訊息正文 + 關聯的全部評論區內容**（完整會話結構）。
- 若原訊息**無評論區**（如頻道訊息或評論功能關閉），則**僅下載訊息正文內容**，與無參數版本行為一致。

---

#### 非下載評論區的推薦寫法

如下表所示:

|   頻道類型   |               連結                |
| :----------: | :-------------------------------: |
|   正常頻道   |       https://t.me/xxx/111        |
|   私密頻道   |   https://t.me/c/xxxxxxxxxx/111   |
|   話題頻道   |     https://t.me/xxx/xxx/111      |
| 私密話題頻道 | https://t.me/c/xxxxxxxxxx/xxx/111 |

---

### 關於`?single`及`?single&comment`參數的下載行為說明

#### 功能變更概述

自`≥v1.5.8`版本起，連結中包含`?single`或`?single&comment`參數時，系統將啟用**單檔案下載模式**。此模式專為以下場景設計與優化：

- 解決`≥1.5.8`版本`/listen_download`當監聽到合併發送的檔案時，出現**重複下載問題**。
- 用戶需求，僅需從合併發送的多媒體組中提取**特定單一檔案**。
- 用戶需求，僅需下載評論區中的**單個指定媒體**（避免評論區媒體過多時，遲遲下載不到想要的檔案）。

#### 參數行為詳解

|       參數格式       |                下載範圍                |           應用場景            |
| :------------------: | :------------------------------------: | :---------------------------: |
|     `xx?single`      |  僅下載訊息正文中的**xx對應媒體檔案**  |  從合併圖組/影片組提取單檔案  |
| `?single&comment=xx` | 僅下載評論區中的**xx所對應的媒體檔案** | 取得評論區單獨分享的圖片/影片 |

#### 版本相容性說明

- 此特性**僅對`≥v1.5.8`版本**生效。
- 歷史版本中這些參數可能被忽略，導致完整內容下載。

#### 最佳實踐建議

##### 單一檔案下載

當訊息包含多個媒體檔案時，使用標準連結附加`?single`參數可精準取得首個檔案：

```
https://t.me/c/123456789/123?single
```

##### 評論區單檔案下載

需從評論區單獨下載檔案時，應採用複合參數格式：

```
https://t.me/c/123456789/123?single&comment=xx
```

##### 參數互斥原則

- 避免同時提交同一訊息的完整版和單檔案版連結（`≥v2.0.8`已針對重複連結導致的資源競爭問題進行自動處理）。
- 單檔案模式與評論區下載模式（`?comment`）不可混用。
   </details>

## 2.5.軟件更新教程

![image](https://raw.githubusercontent.com/Gentlesprite/Telegram_Restricted_Media_Downloader/main/res/2_5_1.png)

# 3.0.在生產環境中執行

_**推薦**使用`Python==3.13.2`作為該項目環境（避免使用其他`Python`版本導致執行時出現報錯）。_

## 對於Windows用戶

_需自行安裝`python`與`git`並設定**環境變量**。_

```shell
git clone https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader.git
cd Telegram_Restricted_Media_Downloader
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```
## 對於Linux用戶

_克隆本專案並**進入項目目錄**。_

```bash
git clone https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader.git
cd Telegram_Restricted_Media_Downloader
```
_**更新**`pip`版本（推薦）。_

```bash
python3 -m pip install --upgrade pip
```

_建立並使用**虛擬環境**（可選）。_

```bash
python3 -m venv venv
source venv/bin/activate
```

_安裝程式執行**所需依賴**並等待全部安裝完成。_

```bash
pip3 install -r requirements.txt
```

_執行程式（到這一步就安裝完成並執行了，後面是注意事項）。_

```bash
python3 main.py
```

### 注意事項

**_如果選擇建立虛擬環境執行，在下次執行時也需要先激活虛擬環境。_**

在項目目錄下，**激活虛擬環境**後再執行程式。

```bash
source venv/bin/activate
python3 main.py
```

_如果提示**沒有安裝pip**使用如下命令進行安裝：_

```bash
sudo apt update
sudo apt-get install python3-pip
```

## 關於更新

_在**項目目錄**下開啟終端機使用如下命令拉取倉庫目前的**最新版本**_：

```shell
git pull
```

_由於新版本可能使用了**新的依賴**，使用`git pull`拉取後，最好更新一下依賴（如果是**虛擬環境**請先激活再執行）。_

```shell
pip3 install -r requirements.txt
```

# 4.0.執行前設定命令列參數（高階用法）

> [!NOTE]
> 自版本`≥v1.8.3`起：  
> 用戶可在**執行前**通過**命令列參數**對**軟件執行設定**進行**更多自訂設定**。\

<details>
<summary><strong>點擊展開</strong></summary>

_**設定命令列執行參數**需先在**軟件目錄**開啟**終端機**，或**任意位置**開啟終端機**進入軟件目錄**（**經常**使用建議**設定環境變量**）。_

**目前支援的**命令列參數用法及解釋如下表所示：

| 短參數  |     長參數     |            解釋            |
|:----:|:-----------:| :------------------------: |
| `-h` |  `--help`   |          展示說明          |
| `-v` | `--version` |        展示版本資訊        |
| `-q` |  `--quiet`  | 跳過重新設定檔的確認提示 |
| `-c` | `--config`  |   設定用戶設定檔的路徑   |
| `-s` | `--session` |     設定會話檔案的路徑     |
| `-t` |  `--temp`   |     設定執行快取的路徑     |
| `-p` |  `--port`   |   設定網頁面板的連接埠   |

_**長參數與短參數最終結果一致。**_

---

## 4.1.參數

#### -h、--help

   該參數用於展示說明。

   - 對於生產環境用戶（**需要先完成前置步驟**[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：

     ```bash
     python3 main.py -h
     ```

     ```bash
     python3 main.py --help
     ```

   - 對於Windows用戶：

     ```bash
     TRMD.exe -h
     ```

     ```bash
     TRMD.exe --help
     ```

   - 對於Linux用戶：

     ```bash
     ./TRMD -h
     ```
     
     ```bash
     ./TRMD --help
     ```

---

#### -v、--version

   該參數用於展示版本資訊。

   - 對於生產環境用戶（**需要先完成前置步驟**[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：

     ```bash
     TRMD.exe -v
     ```

     ```bash
     TRMD.exe --version
     ```

   - 對於Windows用戶：

     ```bash
     TRMD.exe -v
     ```

     ```bash
     TRMD.exe --version
     ```

   - 對於Linux用戶：

     ```bash
     ./TRMD -v
     ```

     ```bash
     ./TRMD --version
     ```

---

#### -q、--quiet
   
   | 使用須知                                         |
   | ------------------------------------------------ |
   | _1.該參數用於跳過重新設定檔的確認提示。_       |
   | _2.用戶設定檔缺少必要參數時，指定該參數無效。_ |
   | _3.該參數為一次性設定，不記憶。_                 |
   
   - 對於生產環境用戶（**需要先完成前置步驟**[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：
   
     ```bash
     python3 main.py -q
     ```
     
     ```bash
     python3 main.py --quiet
     ```
     
   - 對於Windows用戶：
   
     ```bash
     TRMD.exe -q
     ```
     
     ```bash
     TRMD.exe --quiet
     ```
     
   - 對於Linux用戶：
   
     ```bash
     ./TRMD -q
     ```
     
     ```bash
     ./TRMD --quiet
     ```

---

#### -c、--config

   | 使用須知                                                                                                                                                                                                                |
   |---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
   | _1.該參數用於設定用戶設定檔的路徑。_                                                                                                                                                                                               |
   | _2.**該參數旨在解決多個實例（多開）場景下，避免重複部署軟件本體而設計的設定分離方案。**_                                                                                                                                                                    |
   | _3.該參數需指定一個**符合**[“2.3.設定檔說明（用戶設定檔）”](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#%E7%94%A8%E6%88%B7%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6)格式規範的檔案，**並且後綴名需為`.yaml`**。_ |
   | _4.當指定的**檔案路徑無效**時，將使用軟件**預設**設定。_                                                                                                                                                                                  |
   | _5.該參數為一次性設定，不記憶。_                                                                                                                                                                                                  |

   - 對於生產環境用戶（**需要先完成前置步驟**[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：

     以`Linux`系統為例（`Winodws`系統同理），此處假設用戶設定檔位於`/home/username/files/example.yaml`。

     ```bash
     python3 main.py -c /home/username/files/example.yaml
     ```

     ```bash
     python3 main.py --config /home/username/files/example.yaml
     ```

   - 對於Windows用戶：

     此處假設用戶設定檔位於`C:\files\example.yaml`。

     ```bash
     TRMD.exe -c C:\files\example.yaml
     ```

     ```bash
     TRMD.exe --config C:\files\example.yaml
     ```

   - 對於Linux用戶：

      此處假設用戶設定檔位於`/home/username/files/example.yaml`。

      ```bash
      ./TRMD -c /home/username/files/example.yaml
      ```

      ```bash
      ./TRMD --config /home/username/files/example.yaml
      ```

---

#### -s、--session

> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.8.5` | `-s`、`--session`參數在設定後將被儲存到用戶設定檔的`session_directory`參數中，下次使用時無需重複指定，除非需要修改該設定。 |

   | 使用須知                                                                        |
   |-----------------------------------------------------------------------------|
   | _1.該參數用於設定會話檔案的路徑。_                                                         |
   | _2.軟件會在用戶登入成功時後，預設在執行目錄下生成 `session`資料夾，用於儲存目前帳號資訊，以便後續快速登入。_               |
   | _3.**該參數旨在**解決多帳號登入場景下需**手動重命名**會話檔案的問題，使用該參數用戶可通過**直接**指定不同路徑，選擇對應帳號進行登入。_ |
   | _4.該參數需指定一個**資料夾**，可包含已有的 `.session`檔案，指定為空資料夾或不存在時，登入後將在**該路徑自動生成**會話檔案。_  |
   | _5.該參數設定後會被記憶，下次無需重複設定（`≥v1.8.5`）。_                                         |

   - 對於生產環境用戶（**需要先完成前置步驟**"[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：

     以`Linux`系統為例（`Winodws`系統同理），此處假設會話檔案位於`/home/username/files/session`。

     ```bash
     python3 main.py -s /home/username/files/session
     ```

     ```
     python3 main.py --session /home/username/session
     ```

   - 對於Windows用戶：

     此處假設會話檔案位於`C:\files\session`。

     ```bash
     TRMD.exe -s C:\files\session
     ```

     ```bash
     TRMD.exe --session C:\files\session
     ```

   - 對於Linux用戶：

     此處假設會話檔案位於`/home/username/files/session`。

     ```bash
     ./TRMD -s /home/username/files/session
     ```

     ```bash
     ./TRMD --session /home/username/files/session
     ```

---

#### -t、--temp

> **⚠️ 版本變更說明**：

| 版本 | 說明 |
| --- | --- |
| `≥v1.8.5` | `-t`、`--temp`參數在設定後將被儲存到用戶設定檔的`temp_directory`參數中，下次使用時無需重複指定，除非需要修改該設定。 |

   | 使用須知                                                     |
   | ------------------------------------------------------------ |
   | _1.該參數用於設定執行快取的路徑。_                           |
   | _2.快取即軟件執行過程中，記錄**下載和上載**資訊的**儲存中轉站**。_ |
   | _3.**斷點續傳**的實現同樣離不開快取機制的設計，用戶可**根據實際需求自訂快取存放的路徑**。_ |
   | _4.該參數需指定一個**資料夾**，指定為空資料夾或不存在時，執行時將在**該路徑自動生成**生成快取檔案。_ |
   | _5.該參數設定後會被記憶，下次無需重複設定（`≥v1.8.5`）。_    |
   
   - 對於生產環境用戶（**需要先完成前置步驟**[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：
   
     以`Linux`系統為例（`Winodws`系統同理），此處假設快取檔案位於`/home/username/files/temp`。
   
     ```bash
     python3 main.py -t /home/username/files/temp
     ```
   
     ```bash
     python3 main.py --temp /home/username/temp
     ```
   
   - 對於Windows用戶：
   
     此處假設快取檔案位於`C:\files\temp`。
   
     ```bash
     TRMD.exe -t C:\files\temp
     ```
   
     ```bash
     TRMD.exe --temp C:\files\temp
     ```
   
   - 對於Linux用戶：
   
     此處假設快取檔案位於`/home/username/files/temp`。
   
     ```bash
     ./TRMD -t /home/username/files/temp
     ```
   
     ```bash
     ./TRMD --temp /home/username/files/temp
     ```

---

#### -p、--port

  | 使用須知                                                         |
  |--------------------------------------------------------------|
  | _1.網頁面板預設啟用，通過瀏覽器查看下載進度。_                                        |
  | _2.網頁面板會在後台啟動網頁服務，終端機仍可正常操作。_ |
  | _3.`Web設定`資訊會在執行的終端機提供，以便開啟網頁時輸入帳號密碼。_                          |
  | _4.**關閉瀏覽器視窗不會影響程式執行**，程式退出時面板自動關閉。_                          |
  | _5.該參數用於指定網頁面板的**連接埠號**，範圍為`0`~`65535`，若不指定，將使用`2921`連接埠，連接埠被佔用時自動分配。_       |
  | _6.該參數為一次性設定，不記憶。_                                           |
  
  - 對於生產環境用戶（**需要先完成前置步驟**"[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)）：
  
    此處假設使用`1024`連接埠。
  
    ```bash
    python3 main.py -p 1024
    ```
  
    ```bash
    python3 main.py --port 1024
    ```
  
  - 對於Windows用戶：
  
    此處假設使用`1024`連接埠。
  
    ```bash
    TRMD.exe -p 1024
    ```
  
    ```bash
    TRMD.exe --port 1024
    ```
  
  - 對於Linux用戶：
  
    此處假設使用`1024`連接埠。
  
    ```bash
    ./TRMD -p 1024
    ```
  
    ```bash
    ./TRMD --port 1024
    ```
  
  </details>


# 5.0.通過編譯後執行

_**推薦**使用`Python==3.13.2`作為該項目環境，並使用**虛擬環境**，**避免**添加不必要的庫，從而**減小**輸出的檔案大小。_

_`Windows`構建說明：_
   - **Windows構建會啟用`--clang`**。
   - 需安裝`Visual Studio`並勾選`C++ Clang Compiler for Windows`組件以提供`clang-cl`。\
   - 下載`Visual Studio`時須留意版本，其安裝的`LLVM`/`clang`版本須**≥19**，因Nuitka編譯所用的`#embed`（C23）常量嵌入僅在該版本起受支援。\
   - 在`Windows`下，`build.py`必須在**x64 Native Tools Command Prompt for VS**中執行，`Nuitka`依靠該命令列預置的`MSVC`與`Windows SDK`編譯環境。
   - 在`CMD`/`PowerShell`中執行，將因所需環境變量在編譯期報錯，並且`Nuitka`不再回退至`gcc`/`zig`（僅當`MSVC`完全探測不到時才觸發回退）。

同[_“3.0.在生產環境中執行”_](https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader?tab=readme-ov-file#30%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E8%BF%90%E8%A1%8C)**前置步驟一致**。

執行代碼：

```bash
python build.py
```

# 6.0.通過Docker執行

_**Docker環境執行設定檔模板參考（前提：需完全按照後續教程提供的命令啟動Docker）：**_

```yaml
api_hash: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
api_id: 'xxxxxxxx'
bot_token: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
download_type:
- video
- photo
- document
- audio
- voice
- animation
- video_note
- live_photo
is_shutdown: false
links: /app/TRMD/links.txt
max_retries:
  download: 5
  upload: 3
max_tasks:
  download: 3
  upload: 3
proxy:
  enable_proxy: true
  hostname: 192.168.1.10
  scheme: socks5
  port: 10808
  username: null
  password: null
save_directory: /app/downloads/%CHAT_NAME%/%MIME_TYPE%
session_directory: /app/sessions
temp_directory: /app/temp
```

由於`Docker`容器的工作目錄為`/app`，設定檔中的路徑應填寫**容器內路徑**，實際檔案通過`docker run`的`-v`卷掛載映射至宿主機目錄：

| 設定項 | 容器內路徑（寫入設定） | 對應的主機路徑 |
| --- | --- | --- |
| `save_directory` | `/app/downloads/%CHAT_NAME%/%MIME_TYPE%` | `./downloads/%CHAT_NAME%/%MIME_TYPE%` |
| `session_directory` | `/app/sessions` | `./sessions` |
| `temp_directory` | `/app/temp` | `./temp` |
| `links` | `/app/TRMD/links.txt` | `./config/links.txt` |

- _*另掛載`./form:/app/form`為程式內部統計/表單匯出目錄（`/app/form`）。_
- _*代理`hostname`（示例`192.168.1.10`）僅作為參考，實際部署時需替換為各自代理伺服器的`ip`地址（可通過`ip addr`或`ifconfig`查看本機局域網`IP`）。若執行環境已可直接存取`Telegram`伺服器，則可不啟用代理：將`enable_proxy`設為`false`。_

方式1：

- _確保`docker`已安裝並設定**環境變量。**_

- 使用`docker`從遠端倉庫拉取鏡像，注意`TRMD`版本需要`≥2.0.2`：

  ```bash
  docker pull gentlesprite/telegram_restricted_media_downloader:latest
  ```

- 首次使用時需要進入容器設定檔：

  ```bash
  docker run -it --rm \
    --name trmd \
    -v ./config:/app/TRMD \
    -v ./sessions:/app/sessions \
    -v ./downloads:/app/downloads \
    -v ./temp:/app/temp \
    -v ./form:/app/form \
    -p 127.0.0.1:2921:2921 \
    -e TZ=Asia/Shanghai \
    -e TRMD_WEB_HOST=0.0.0.0 \
    gentlesprite/telegram_restricted_media_downloader:latest \
    python main.py --config /app/TRMD/config.yaml --port 2921
  ```

- 如果是通過`Windows`使用`wsl2`執行`docker`：

  ```bash
  docker run -it --rm --name trmd -v ./config:/app/TRMD -v ./sessions:/app/sessions -v ./downloads:/app/downloads -v ./temp:/app/temp -v ./form:/app/form -p 127.0.0.1:2921:2921 -e TZ=Asia/Shanghai -e TRMD_WEB_HOST=0.0.0.0 gentlesprite/telegram_restricted_media_downloader:latest python main.py --config /app/TRMD/config.yaml --port 2921
  ```

- 如果已設定完成的情況下，直接建立並啟動容器：

  ```bash
  docker run -it -d \
    --name trmd \
    -v ./config:/app/TRMD \
    -v ./sessions:/app/sessions \
    -v ./downloads:/app/downloads \
    -v ./temp:/app/temp \
    -v ./form:/app/form \
    -p 127.0.0.1:2921:2921 \
    -e TZ=Asia/Shanghai \
    -e TRMD_WEB_HOST=0.0.0.0 \
    gentlesprite/telegram_restricted_media_downloader:latest \
    python main.py --config /app/TRMD/config.yaml --port 2921
  ```

- 如果是通過`Windows`使用`wsl2`執行`docker`：

  ```bash
  docker run -it -d --name trmd -v ./config:/app/TRMD -v ./sessions:/app/sessions -v ./downloads:/app/downloads -v ./temp:/app/temp -v ./form:/app/form -p 127.0.0.1:2921:2921 -e TZ=Asia/Shanghai -e TRMD_WEB_HOST=0.0.0.0 gentlesprite/telegram_restricted_media_downloader:latest python main.py --config /app/TRMD/config.yaml --port 2921
  ```

方式2：

- _確保`git`、`docker`、`docker-compose`已安裝並設定**環境變量。**_

- 使用`git`克隆倉庫：

  ```bash
  git clone https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader.git
  ```

- 進入項目資料夾：

  ```bash
  cd Telegram_Restricted_Media_Downloader
  ```

- 首次使用時需要進入容器設定檔：

  ```bash
  docker-compose run --rm --service-ports --name trmd trmd
  ```

- 如果已設定完成的情況下，直接建立並啟動容器：

  ```bash
  docker-compose up -d
  ```

以上兩種方式啟動後，通過在終端機或在`Telegram`中向機械人發送`/help`命令查看`Web設定`以存取網頁面板（包含連接埠、帳號、密碼與存取連結），類似下表：

| 屬性 | 內容                    |
|----| ----------------------- |
| 連接埠 | `2921`                  |
| 帳號 | `cLJqKG3b`              |
| 密碼 | `AiJaKSObcRCZ`          |
| 連結 | `http://127.0.0.1:2921` |

_帳號密碼由系統隨機產生；使用瀏覽器前往[http://127.0.0.1:2921](http://127.0.0.1:2921)，輸入帳號密碼即可登入。_

- **僅在已設定機械人的情況下**，也可在`Telegram`中向機械人發送`/help`命令查看上述`Web設定`。
- 網頁面板預設使用`2921`連接埠，可通過`-p`、`--port`參數指定自訂連接埠，連接埠被佔用時自動分配可用連接埠。
- 網頁面板在後台啟動網頁服務，終端機仍可正常操作；**關閉瀏覽器視窗不會影響程式執行**，程式退出時面板自動關閉。
- 首次以帳號密碼登入後，面板會向**此瀏覽器**發送有效期為`30`天的`Cookie`；重新啟動程式或再次造訪時，仍可免登入。
- 網頁管理後台可檢視服務狀態、管理下載與上載工作，並調整可即時套用或需重新啟動的設定；單項工作支援暫停、繼續與取消。
- 後台亦可安全停止服務或重新連線機械人；程式本身仍須由命令列、Docker 或服務管理器啟動。
- 非 Docker 環境預設只監聽`127.0.0.1`；可透過`--host`或`TRMD_WEB_HOST`指定監聽位址。Docker 容器需監聽`0.0.0.0`才能轉送連線，本文範例則將主機連接埠限制在`127.0.0.1`。
- **請勿直接將未加密的 HTTP 管理介面暴露於公網。**遠端管理請使用 VPN 或具 HTTPS 與存取控制的反向代理，並妥善保管終端機顯示的登入憑證。

其他命令：

- 如需查看執行日誌：

  ```bash
  docker logs trmd
  ```

- **不再使用**時，停止並刪除容器：

  ```bash
  docker stop trmd && docker rm trmd
  ```

# 7.0.聯絡作者

  Telegram：[@Gentlesprite](https://t.me/Gentlesprite)

  電郵：Gentlesprites@outlook.com
