import os
import re
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from auth import MailTM

if getattr(sys, 'frozen', False):
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(
        os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright'
    )

WORKSPACE_URL = "https://vmake.ai/workspace"
DEFAULT_WORKSPACE_PROMPT = (
    "Remove all text and watermarks from this video, and enhance the video sharpness and clarity while "
    "keeping the original content unchanged."
)

async def _human_delay():
    await asyncio.sleep(3.5)


async def auto_login(page, log_callback):
    email = "unknown"
    try:
        mail = MailTM()
        email = mail.address
        if log_callback:
            log_callback(f"Hệ thống tạo email ảo: {email}")
            log_callback("Đang thử đăng nhập/đăng ký tự động...")

        await page.goto("https://vmake.ai/", timeout=60000)
        await _human_delay()

        try:
            login_btn = page.get_by_text("Log in", exact=True).first
            await login_btn.wait_for(state="visible", timeout=10000)
            await login_btn.click()
            await _human_delay()
        except Exception:
            pass

        if log_callback:
            log_callback("Đang chờ form đăng nhập hiện lên...")

        continue_email_btn = page.get_by_text("Continue with email").first
        await continue_email_btn.wait_for(state="visible", timeout=30000)
        await continue_email_btn.click()
        await _human_delay()

        email_input = page.locator('input[type="email"], input[placeholder*="email" i]').first
        await email_input.wait_for(state="visible", timeout=7000)
        await email_input.fill(email)

        send_btn = page.locator('button:has-text("Send"), button:has-text("Continue"), button:has-text("Get code")').first
        await send_btn.click()
        if log_callback:
            log_callback(f"Đã gửi yêu cầu mã xác nhận đến {email}.")

        msg_id = None
        for _ in range(60):
            await asyncio.sleep(2)
            msgs = mail.check_mailbox()
            if msgs:
                msg_id = msgs[0]["id"]
                break

        if not msg_id:
            if log_callback:
                log_callback("Không nhận được email OTP.")
            return False

        email_data = mail.read_email(msg_id)
        text_body = email_data.get("text", "")
        compact_body = text_body.replace(" ", "").replace("\n", "").replace("\r", "")
        codes = [c for c in re.findall(r"(?<!\d)\d{4,6}(?!\d)", compact_body) if not c.startswith("202")]
        if not codes:
            if log_callback:
                log_callback("Không parse được OTP.")
            return False

        code_input = page.locator('input[type="text"], input[name*="code" i]').first
        await code_input.wait_for(state="visible", timeout=7000)

        # Gõ OTP như người dùng thật để tránh một số UI không nhận fill().
        otp = codes[0]
        await code_input.click()
        try:
            await code_input.fill("")
        except Exception:
            pass
        await page.keyboard.type(otp, delay=110)
        if log_callback:
            log_callback(f"Đã điền OTP: {otp}")
        await _human_delay()

        submit_btn = page.locator(
            "button.starii-account-email-verify-code-check-view-submit, "
            ".starii-account-login-popup button:has-text('Log in'), "
            ".starii-account-login-popup button:has-text('Sign in'), "
            "button:has-text('Log in'), button:has-text('Sign in')"
        ).first

        # Retry submit OTP nhiều lần: Enter -> click force -> JS click/submit form.
        for _ in range(12):
            if ("/workspace" in page.url) or ("/ai-agent" in page.url):
                break
            if log_callback:
                log_callback("Đang submit OTP...")

            # 1) Enter ở input OTP
            try:
                await code_input.press("Enter")
            except Exception:
                pass
            await asyncio.sleep(1.2)
            if ("/workspace" in page.url) or ("/ai-agent" in page.url):
                break

            # 2) Click vào đúng nút submit OTP nếu thấy
            try:
                if await submit_btn.is_visible(timeout=800):
                    # Nếu nút đang disabled thì chờ thêm.
                    try:
                        disabled = await submit_btn.get_attribute("disabled")
                        if disabled is not None:
                            await asyncio.sleep(0.8)
                    except Exception:
                        pass
                    await submit_btn.click(force=True, timeout=2500)
                    if log_callback:
                        log_callback("Đã click nút Log in (Playwright).")
            except Exception:
                pass
            await asyncio.sleep(1.2)
            if ("/workspace" in page.url) or ("/ai-agent" in page.url):
                break

            # 3) Fallback JS: click trực tiếp đúng class nút submit OTP
            try:
                await page.evaluate(
                    """
                    () => {
                      let target = document.querySelector('button.starii-account-email-verify-code-check-view-submit');
                      if (!target) {
                        const root = document.querySelector('.starii-account-login-popup') || document;
                        const btns = Array.from(root.querySelectorAll('button'));
                        target = btns.find(b => /log\\s*in|sign\\s*in/i.test((b.textContent || '').trim()));
                      }
                      if (target) {
                        target.click();
                        const form = target.closest('form');
                        if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                      }
                    }
                    """
                )
                if log_callback:
                    log_callback("Đã click nút Log in (JS fallback).")
            except Exception:
                pass
            await asyncio.sleep(1.5)

        if ("/workspace" not in page.url) and ("/ai-agent" not in page.url):
            if log_callback:
                log_callback("Chưa chuyển trang sau khi submit OTP, đợi điều hướng thêm...")
            try:
                await page.wait_for_url("**/workspace**", timeout=15000)
            except Exception:
                await page.wait_for_url("**/ai-agent**", timeout=15000)

        await _human_delay()
        if log_callback:
            log_callback("Đăng nhập thành công, đã vào workspace.")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi đăng nhập tự động: {str(e)}")
            log_callback(f"VUI LÒNG DÙNG EMAIL NÀY ĐỂ TỰ ĐĂNG KÝ: {email}")
        return False


async def _click_plus_upload(page, log_callback=None):
    plus_candidates = [
        page.locator('div.agent-chat-add-file-box--Fysd9').first,
        page.locator('div[class*="agent-chat-add-file-box--"]').first,
    ]
    for btn in plus_candidates:
        try:
            if await btn.is_visible(timeout=2500):
                return btn
        except Exception:
            pass
    if log_callback:
        log_callback("Không tìm thấy nút + upload.")
    return None


async def _upload_file_via_plus(page, file_path, log_callback=None):
    plus_btn = await _click_plus_upload(page, log_callback=log_callback)
    if plus_btn is None:
        raise Exception("Không tìm thấy nút + để upload")

    # B3: pass popup bằng expect_file_chooser
    try:
        async with page.expect_file_chooser(timeout=6000) as fc_info:
            await plus_btn.click(force=True)
        chooser = await fc_info.value
        await chooser.set_files(file_path)
        await _human_delay()
        if log_callback:
            log_callback("Đã upload file qua file chooser.")
        return
    except Exception:
        pass

    # fallback input
    file_input = page.locator('input[type="file"]').first
    await file_input.wait_for(state="attached", timeout=15000)
    await file_input.set_input_files(file_path)
    await _human_delay()
    if log_callback:
        log_callback("Đã upload file qua input[type=file] fallback.")


async def _fill_prompt(page, prompt_text, log_callback=None):
    prompt_box = page.locator(
        'textarea.agent-chat-textarea--mCwt5[placeholder*="Describe your video idea" i], '
        'textarea[class*="agent-chat-textarea--"][placeholder*="Describe your video idea" i]'
    ).first

    await prompt_box.wait_for(state="visible", timeout=20000)
    await prompt_box.click()
    await prompt_box.fill(prompt_text)
    await _human_delay()
    if log_callback:
        log_callback("Đã nhập prompt vào textarea.")


async def _send_prompt(page, log_callback=None):
    send_btn = page.locator(
        'div.agent-chat-send--MKtzm, div[class*="agent-chat-send--"]'
    ).first
    await send_btn.wait_for(state="visible", timeout=30000)

    # Chỉ bấm khi nút send sẵn sàng (không disabled và click được).
    send_ready = False
    for _ in range(60):  # ~3 phút
        try:
            is_ready = await send_btn.evaluate(
                """
                (el) => {
                  const disabledByAttr = el.getAttribute('aria-disabled') === 'true' || el.getAttribute('disabled') !== null;
                  const cls = (el.className || '').toString().toLowerCase();
                  const disabledByClass = cls.includes('disabled');
                  const r = el.getBoundingClientRect();
                  const cx = r.left + r.width / 2;
                  const cy = r.top + r.height / 2;
                  const topEl = document.elementFromPoint(cx, cy);
                  const clickable = !!topEl && (el === topEl || el.contains(topEl) || topEl.contains(el));
                  return (!disabledByAttr) && (!disabledByClass) && clickable;
                }
                """
            )
            if is_ready:
                send_ready = True
                break
        except Exception:
            pass
        await asyncio.sleep(3)

    if not send_ready:
        raise Exception("Nút send chưa sẵn sàng sau khi upload/prompt.")

    await send_btn.click(force=True)
    await _human_delay()
    if log_callback:
        log_callback("Đã bấm nút send.")


async def _wait_redirect_to_result_page(page, log_callback=None):
    # B6: hiện tại chủ yếu sang ai-agent, vẫn giữ fallback captions-editor.
    try:
        await page.wait_for_url("**/ai-agent**", timeout=180000)
        target = "ai-agent"
    except Exception:
        await page.wait_for_url("**/video-captions-editor**", timeout=180000)
        target = "video-captions-editor"
    await _human_delay()
    if log_callback:
        log_callback(f"Đã chuyển sang {target}.")

async def _wait_ai_processing_done(page, log_callback=None):
    """
    Chờ job xử lý xong trên ai-agent trước khi export.
    Điều kiện hoàn tất DUY NHẤT: thấy text 'Mission Completed'.
    """
    if "/ai-agent" not in page.url:
        return

    if log_callback:
        log_callback("Đang chờ AI xử lý xong (đợi Mission Completed)...")

    for _ in range(240):  # tối đa ~20 phút, check mỗi 5s
        mission_done = False
        try:
            mission_done = await page.get_by_text("Mission Completed", exact=False).first.is_visible(timeout=500)
        except Exception:
            mission_done = False

        if mission_done:
            await asyncio.sleep(3)
            if log_callback:
                log_callback("Đã thấy Mission Completed.")
            return

        await asyncio.sleep(5)

    raise Exception("Timeout: chưa thấy Mission Completed trên ai-agent.")


async def _download_from_result_page(page, download_dir, src_file_path, log_callback=None):
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    out_name = f"watermark_removed_{os.path.basename(src_file_path)}"
    out_path = os.path.join(download_dir, out_name)

    # B7 theo yêu cầu: click nút download cuối cùng trong player khi đã Mission Completed
    last_err = None

    # Retry chờ UI render nút download của block mới nhất.
    for round_idx in range(50):  # ~4-5 phút
        try:
            btn_count = await page.locator('div[class*="video-play_download__"]').count()
        except Exception:
            btn_count = 0

        if btn_count > 0:
            for i in range(btn_count - 1, -1, -1):  # duyệt từ cuối lên đầu
                btn = page.locator('div[class*="video-play_download__"]').nth(i)
                try:
                    if not await btn.is_visible(timeout=1000):
                        continue
                    await btn.scroll_into_view_if_needed(timeout=10000)
                    await asyncio.sleep(1.2)
                    async with page.expect_download(timeout=120000) as dlinfo:
                        await btn.click(force=True)
                    dl = await dlinfo.value
                    await dl.save_as(out_path)
                    if log_callback:
                        log_callback(f"Đã download từ nút player mới nhất (index={i}).")
                    return out_path
                except Exception as e:
                    last_err = str(e)
                    continue

        if log_callback and round_idx % 8 == 0:
            log_callback("Chưa bắt được nút download trong player, tiếp tục chờ...")
        await asyncio.sleep(5)

    # Fallback cuối: thử Export để không mất job.
    try:
        if log_callback:
            log_callback("Fallback sang Export vì chưa thấy nút download trong player.")
        export_btn = page.locator('button:has-text("Export"), a:has-text("Export")').first
        await export_btn.wait_for(state="visible", timeout=20000)
        async with page.expect_download(timeout=180000) as dlinfo:
            await export_btn.click(force=True)
        dl = await dlinfo.value
        await dl.save_as(out_path)
        if log_callback:
            log_callback("Đã download bằng fallback Export.")
        return out_path
    except Exception as e:
        last_err = str(e)

    raise Exception(f"Không bắt được download từ player và Export: {last_err}")


async def process_all_chunks(chunk_paths, download_dir, log_callback=None, progress_callback=None, prompt_text=None):
    if not chunk_paths:
        return []

    input_file = chunk_paths[0]
    final_prompt = (prompt_text or "").strip() or DEFAULT_WORKSPACE_PROMPT

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    ok = await auto_login(page, log_callback)
    if not ok:
        if progress_callback:
            progress_callback(1, 1)
        return []

    if "/workspace" not in page.url:
        await page.goto(WORKSPACE_URL, timeout=60000)

    await _upload_file_via_plus(page, input_file, log_callback=log_callback)
    await _fill_prompt(page, final_prompt, log_callback=log_callback)
    await _send_prompt(page, log_callback=log_callback)
    await _wait_redirect_to_result_page(page, log_callback=log_callback)
    await _wait_ai_processing_done(page, log_callback=log_callback)
    output_path = await _download_from_result_page(page, download_dir, input_file, log_callback=log_callback)

    if progress_callback:
        progress_callback(1, 1)

    # Giữ browser mở để debug thủ công. Không close context/browser/p ở đây.
    return [output_path]
