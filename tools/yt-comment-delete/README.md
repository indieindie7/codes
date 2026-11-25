# YT Comment Delete

A one-click Chrome bookmarklet. It deletes all of your own YouTube comments from Google My Activity (`myactivity.google.com/page?page=youtube_comments`).

## Use
1. Open `yt-comment-delete.html` in Chrome.
2. Drag the red **Delete YT comments** button to your bookmarks bar.
3. Click it once to open your comments page, then click it again on that page to start.
4. The tab title shows the count. Click the button again to stop.
5. Keep the tab open until the "Leave site?" warning stops appearing. Google sends the deletes one at a time, about one every 2–3 s, and closing the tab drops the ones still queued.

## How it works
- It finds the first visible `button[aria-label*="Delete activity item"]`. A plain `.click()` is ignored, so it sends the full pointer/mouse event sequence instead.
- It waits until that item leaves the page (up to 600 ms), pauses 250 ms, then moves on to the next one.
- When no buttons are left, it scrolls to load more, and stops after 30 empty tries.
- It runs only in your browser. It makes no network calls of its own and never sends your data anywhere.

## Notes
- The deletes are permanent, and the script runs on the comments page only.
- Clicking faster than this doesn't help, because the server queue sets the speed.
- Used on 2026-11-24 (Chrome, English UI). A fresh reload confirmed the deletes reached the server. The bookmark button itself has not been tested. If your UI is in another language, the aria-label text is different: edit the selector.
