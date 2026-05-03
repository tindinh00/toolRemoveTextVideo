import os
import asyncio
import re
import sys
import random

# Đảm bảo Playwright tìm trình duyệt ở thư mục hệ thống (quan trọng khi chạy từ .exe)
if getattr(sys, 'frozen', False):
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(
        os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright'
    )

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from auth import MailTM

async def auto_login(page, log_callback):
    """Tiến trình đăng ký/đăng nhập tự động bằng email ảo"""
    email = "unknown"
    try:
        mail = MailTM()
        email = mail.address
        if log_callback:
            log_callback(f"Hệ thống tạo email ảo: {email}")
            log_callback("Đang thử đăng nhập/đăng ký tự động...")

        # Vào trang chủ của vmake.ai theo đúng ảnh bạn gửi
        await page.goto("https://vmake.ai/", timeout=60000)
        await asyncio.sleep(2)
        
        try:
            # Click vào nút "Log in" rõ ràng trên thanh menu
            login_btn = page.get_by_text("Log in", exact=True).first
            await login_btn.wait_for(state="visible", timeout=10000)
            await asyncio.sleep(1)
            await login_btn.click()
            await asyncio.sleep(2)
        except Exception as e:
            pass
            
        if log_callback:
            log_callback("Đang chờ form đăng nhập hiện lên (Nếu tool không tự click được, BẠN HÃY TỰ CLICK VÀO AVATAR nhé!)...")
            
        # Chờ và click "Continue with email" trong popup (Cho phép người dùng tự bấm với thời gian 30s)
        continue_email_btn = page.get_by_text("Continue with email").first
        await continue_email_btn.wait_for(state="visible", timeout=30000)
        await asyncio.sleep(1)
        await continue_email_btn.click()
        await asyncio.sleep(2)
            
        # Nhập email
        email_input = page.locator('input[type="email"], input[placeholder*="email" i]').first
        await email_input.wait_for(state="visible", timeout=5000)
        await asyncio.sleep(1)
        await email_input.fill(email)
        await asyncio.sleep(1)
        
        # Bấm gửi
        send_btn = page.locator('button:has-text("Send"), button:has-text("Continue"), button:has-text("Get code")').first
        await send_btn.click()
        await asyncio.sleep(2)
        
        if log_callback:
            log_callback(f"Đã gửi yêu cầu mã xác nhận đến {email}.")
            log_callback(f"Đang chờ thư... (NẾU BỊ BẮT XÁC MINH CAPTCHA, BẠN CỨ KÉO CHUỘT GIẢI MÃ NHÉ!)")

        msg_id = None
        # Chờ tối đa 120s để bạn có thời gian tự giải Captcha nếu web yêu cầu
        for _ in range(60):
            await asyncio.sleep(2)
            msgs = mail.check_mailbox()
            if msgs:
                msg_id = msgs[0]['id']
                break

        if not msg_id:
            if log_callback:
                log_callback("Không nhận được email. Tool sẽ tiếp tục bằng quyền Khách.")
            return

        email_data = mail.read_email(msg_id)
        text_body = email_data.get('text', '')
        
        if log_callback:
            # In ra đoạn thư dài hơn để chắc chắn bạn thấy được OTP
            clean_text = text_body.replace('\n', ' ').strip()
            log_callback(f"Nội dung thư: {clean_text[:400]}")
        
        # Vmake có thể gửi mã có khoảng trắng (ví dụ: 1 6 3 8). Ta xóa hết khoảng trắng đi để dễ quét.
        compact_body = text_body.replace(' ', '').replace('\n', '').replace('\r', '')
        # Quét tìm mã 4 hoặc 6 số. Loại trừ năm 202x
        codes = [c for c in re.findall(r'(?<!\d)\d{4,6}(?!\d)', compact_body) if not c.startswith('202')]
        if codes:
            code = codes[0]
            if log_callback:
                log_callback(f"==> TOOL DỰ ĐOÁN MÃ LÀ: {code} <==")
                log_callback(f"Nếu sai, bạn hãy đọc nội dung thư ở trên và tự nhập nhé!")
                
            code_input = page.locator('input[type="text"], input[name*="code" i]').first
            if await code_input.is_visible(timeout=5000):
                await asyncio.sleep(1)
                await code_input.fill(code)
                await asyncio.sleep(1)
                
                # Bấm Enter sau khi nhập xong phòng khi web hỗ trợ
                await code_input.press("Enter")
                await asyncio.sleep(1)
                
                # Cố gắng click nút Submit nếu web không tự động đăng nhập
                try:
                    # Lấy nút Log in bên trong popup
                    submit_btn = page.locator('.starii-account-login-popup button:has-text("Log in"), button:has-text("Sign in")').last
                    if await submit_btn.is_visible(timeout=2000):
                        await submit_btn.click(timeout=3000, force=True)
                except:
                    # Nếu lỗi (ví dụ popup đã tự đóng) thì bỏ qua
                    pass
                
                await asyncio.sleep(5)
                if log_callback:
                    log_callback("Tự động điền mã thành công!")
        else:
            if log_callback:
                log_callback("Không thấy OTP trong thư. Vui lòng kiểm tra màn hình hoặc thao tác tay!")
                
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi đăng nhập tự động: {str(e)}")
            log_callback(f"VUI LÒNG DÙNG EMAIL NÀY ĐỂ TỰ ĐĂNG KÝ: {email}")
            log_callback("Tool sẽ kiểm tra hòm thư và in mã OTP ra đây...")
            
async def upload_chunk_in_new_tab(context, chunk_path, idx, total, log_callback):
    """Mở tab mới và upload video, không chờ render xong."""
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    filename = os.path.basename(chunk_path)
    if log_callback:
        log_callback(f"[{idx+1}/{total}] Mở tab và chuẩn bị upload {filename}...")

    await page.goto("https://vmake.ai/video-watermark-remover/upload", timeout=120000)
    await asyncio.sleep(random.uniform(3, 4))
    file_input = page.locator('input[type="file"]').first
    await file_input.wait_for(state="attached", timeout=60000)

    try:
        cookie_btn = page.get_by_text("Accept", exact=True).first
        if await cookie_btn.is_visible(timeout=2000):
            await cookie_btn.click()
    except:
        pass

    await file_input.set_input_files(chunk_path)
    # UI có thể không hiện đủ tên file hoặc hiện rất trễ, nên chỉ đợi nhẹ để ổn định.
    await asyncio.sleep(1.2)
    if log_callback:
        log_callback(f"[{idx+1}/{total}] Upload xong {filename}, chuyển sang tab kế tiếp...")
    return page, filename

async def get_login_state(browser, log_callback, account_idx=1):
    """Đăng nhập 1 tài khoản và trả về storage_state để tái sử dụng."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    if log_callback:
        log_callback(f"Đang chuẩn bị tài khoản tách biệt #{account_idx}...")

    await auto_login(page, log_callback)
    await asyncio.sleep(5)
    state = await context.storage_state()
    await context.close()
    return state

async def wait_and_download_from_tab(
    page, filename, download_dir, idx, total, log_callback,
    progress_callback, state_tracker, download_mode="free_5s"
):
    """Theo dõi tab đã upload và tải về khi sẵn sàng."""
    download_path = None
    try:
        if download_mode == "full":
            download_btn = page.get_by_text("Download full video", exact=False).first
        else:
            download_btn = page.get_by_text("Download 5s", exact=False).first
        upload_failed = page.get_by_text("Upload Failed", exact=False).first

        is_ready = False
        for _ in range(60):  # tối đa 5 phút
            if await download_btn.is_visible(timeout=1000):
                is_ready = True
                break
            if await upload_failed.is_visible(timeout=500):
                raise Exception("Upload Failed")
            await asyncio.sleep(5)

        if not is_ready:
            raise Exception("Timeout")

        if log_callback:
            log_callback(f"[{idx+1}/{total}] Render xong {filename}, đang tải...")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        dest_path = os.path.join(download_dir, filename)

        downloaded = False
        click_attempts = [
            {"force": True, "delay_ms": 0},
            {"force": False, "delay_ms": 0},
            {"force": True, "delay_ms": 100},
        ]
        for attempt_idx, click_opts in enumerate(click_attempts):
            try:
                if log_callback:
                    log_callback(f"[{idx+1}/{total}] Thử tải lần {attempt_idx + 1}...")
                async with page.expect_download(timeout=120000) as download_info:
                    await download_btn.click(force=click_opts["force"], delay=click_opts["delay_ms"])
                download = await download_info.value
                await download.save_as(dest_path)
                downloaded = True
                break
            except Exception:
                await asyncio.sleep(1.5)

        # Fallback: một số trường hợp site không phát event download, thử lấy href trực tiếp
        if not downloaded:
            try:
                direct_url = await download_btn.get_attribute("href")
                if direct_url:
                    if log_callback:
                        log_callback(f"[{idx+1}/{total}] Không bắt được event download, thử tải trực tiếp...")
                    download_resp = await page.request.get(direct_url, timeout=120000)
                    if download_resp.ok:
                        body = await download_resp.body()
                        with open(dest_path, "wb") as f:
                            f.write(body)
                        downloaded = True
            except Exception:
                pass

        if not downloaded:
            raise Exception("Không bắt được tiến trình tải file (download event không xuất hiện).")

        download_path = dest_path
    except Exception as e:
        if log_callback:
            log_callback(f"[{idx+1}/{total}] Lỗi {filename}: {str(e)}")
    finally:
        state_tracker['completed'] += 1
        if progress_callback:
            progress_callback(state_tracker['completed'], total)
        await page.close()

    return download_path

async def wait_until_ready(page, idx, total, log_callback, download_mode="free_5s"):
    if download_mode == "full":
        download_btn = page.get_by_text("Download full video", exact=False).first
    else:
        download_btn = page.get_by_text("Download 5s", exact=False).first
    upload_failed = page.get_by_text("Upload Failed", exact=False).first

    is_ready = False
    for _ in range(60):  # tối đa 5 phút
        if await download_btn.is_visible(timeout=1000):
            is_ready = True
            break
        if await upload_failed.is_visible(timeout=500):
            raise Exception("Upload Failed")
        await asyncio.sleep(5)

    if not is_ready:
        raise Exception("Timeout chờ AI xử lý xong")
    if log_callback:
        log_callback(f"[{idx+1}/{total}] AI xử lý xong.")

async def wait_until_ready_for_uploaded_file(page, filename, idx, total, log_callback, download_mode="free_5s"):
    """
    Chỉ coi là ready khi:
    1) Đúng tên file hiện tại đang hiện trên tab
    2) Nút download tương ứng của chính file đó xuất hiện
    """
    if download_mode == "full":
        download_btn = page.get_by_text("Download full video", exact=False).first
    else:
        download_btn = page.get_by_text("Download 5s", exact=False).first
    upload_failed = page.get_by_text("Upload Failed", exact=False).first

    # Bắt vòng đời xử lý thật: cố gắng thấy Loading... xuất hiện rồi biến mất
    loading_seen = False
    for _ in range(24):  # ~2 phút đầu để bắt loading cycle
        try:
            if await page.get_by_text("Loading...", exact=False).first.is_visible(timeout=1000):
                loading_seen = True
                break
        except Exception:
            pass
        await asyncio.sleep(2)

    if loading_seen:
        try:
            await page.get_by_text("Loading...", exact=False).first.wait_for(state="hidden", timeout=240000)
        except Exception:
            pass

    is_ready = False
    stable_count = 0
    for _ in range(90):
        if await upload_failed.is_visible(timeout=500):
            raise Exception(f"Upload Failed ({filename})")
        visible = await download_btn.is_visible(timeout=1200)
        if visible:
            stable_count += 1
            if stable_count >= 2:
                is_ready = True
                break
        else:
            stable_count = 0
        await asyncio.sleep(3)

    if not is_ready:
        raise Exception(f"Timeout chờ AI xử lý xong ({filename})")
    if log_callback:
        log_callback(f"[{idx+1}/{total}] AI xử lý xong đúng file {filename}.")

async def download_all_from_final_tab(
    page, expected_count, output_names, download_dir,
    log_callback, progress_callback, state_tracker, download_mode="free_5s"
):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    button_text = "Download full video" if download_mode == "full" else "Download 5s"
    download_buttons = page.get_by_text(button_text, exact=False)

    # Đợi list nút download xuất hiện đủ (hoặc tối thiểu 1)
    for _ in range(30):
        try:
            cnt = await download_buttons.count()
        except Exception:
            cnt = 0
        if cnt > 0:
            break
        await asyncio.sleep(2)

    results = []

    async def click_item_by_name(target_name):
        # Chọn đúng item theo tên file trước khi bấm download
        item = page.get_by_text(target_name, exact=False).first
        await item.wait_for(state="visible", timeout=30000)
        await item.scroll_into_view_if_needed(timeout=10000)
        await asyncio.sleep(0.3)
        await item.click(force=True)
        await asyncio.sleep(0.8)

    async def wait_item_ready_before_download(target_name):
        """
        Chờ 3-4s rồi xác nhận item mục tiêu thật sự sẵn sàng tải,
        tránh trường hợp UI báo xong sớm nhưng backend chưa cấp link download.
        """
        await asyncio.sleep(random.uniform(3, 4))
        button_text_local = "Download full video" if download_mode == "full" else "Download 5s"
        for _ in range(24):  # tối đa ~2 phút
            await page.bring_to_front()
            await click_item_by_name(target_name)
            try:
                await page.get_by_text("Loading...", exact=False).first.wait_for(state="hidden", timeout=10000)
            except Exception:
                pass
            btn = page.get_by_text(button_text_local, exact=False).first
            if await btn.is_visible(timeout=1500):
                return
            await asyncio.sleep(5)
        raise Exception(f"Item chưa sẵn sàng tải: {target_name}")

    # Ổn định toàn bộ trang trước khi vào vòng tải
    await asyncio.sleep(random.uniform(3, 4))
    for i in range(expected_count):
        target_name = output_names[i]
        dest_path = os.path.join(download_dir, target_name)
        downloaded = False

        # Mỗi lần luôn bấm nút đầu tiên của danh sách hiện tại.
        # Sau khi download, item thường chuyển trạng thái/biến mất khỏi vị trí đầu.
        for attempt in range(3):
            try:
                await page.bring_to_front()
                await wait_item_ready_before_download(target_name)
                try:
                    await page.get_by_text("Loading...", exact=False).first.wait_for(state="hidden", timeout=15000)
                except Exception:
                    pass

                # Quan trọng: phải chọn đúng video mục tiêu để tránh tải lặp video trước đó
                await click_item_by_name(target_name)

                btn = page.get_by_text(button_text, exact=False).first
                await btn.wait_for(state="visible", timeout=15000)
                await btn.scroll_into_view_if_needed(timeout=10000)
                await asyncio.sleep(0.4)
                async with page.expect_download(timeout=120000) as download_info:
                    await btn.click(force=True)
                download = await download_info.value
                await download.save_as(dest_path)
                downloaded = True
                results.append(dest_path)
                if log_callback:
                    log_callback(f"[{i+1}/{expected_count}] Đã tải {target_name}")
                break
            except Exception:
                await asyncio.sleep(1.5)

        state_tracker['completed'] += 1
        if progress_callback:
            progress_callback(state_tracker['completed'], expected_count)

        if not downloaded and log_callback:
            log_callback(f"[{i+1}/{expected_count}] Không tải được {target_name}")

    return results

async def process_single_chunk_isolated(
    browser, login_state, chunk_path, download_dir, idx, total, log_callback,
    progress_callback, state_tracker, download_mode="free_5s"
):
    """
    Mỗi video chạy trong context riêng để tránh trùng kết quả giữa các tab/video.
    """
    context = await browser.new_context(
        storage_state=login_state,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    try:
        page, filename = await upload_chunk_in_new_tab(context, chunk_path, idx, total, log_callback)
        return await wait_and_download_from_tab(
            page, filename, download_dir, idx, total, log_callback,
            progress_callback, state_tracker, download_mode=download_mode
        )
    finally:
        await context.close()

async def upload_batch_on_same_page(page, batch_paths, start_idx, total, log_callback):
    if log_callback:
        log_callback(f"Đang upload đợt mới ({len(batch_paths)} video)...")

    # Đợi trang ổn định trước khi upload batch
    await asyncio.sleep(random.uniform(1, 2))

    # Ưu tiên thao tác với UI button Upload/Batch upload nếu có
    try:
        batch_btn = page.get_by_text("Batch upload", exact=False).first
        if await batch_btn.is_visible(timeout=2000):
            await batch_btn.click()
            await asyncio.sleep(0.5)
    except Exception:
        pass

    file_input = page.locator('input[type="file"]').first
    await file_input.wait_for(state="attached", timeout=60000)
    await file_input.set_input_files(batch_paths)

    for offset, path in enumerate(batch_paths):
        idx = start_idx + offset
        if log_callback:
            log_callback(f"[{idx+1}/{total}] Đã import {os.path.basename(path)}")

async def wait_ready_for_filename(page, filename, idx, total, log_callback, download_mode="free_5s"):
    button_text = "Download full video" if download_mode == "full" else "Download 5s"
    card = page.locator("div").filter(has_text=filename).first

    ready = False
    for _ in range(90):  # ~7.5 phút
        try:
            btn = card.get_by_text(button_text, exact=False).first
            if await btn.is_visible(timeout=500):
                ready = True
                break
        except Exception:
            pass
        await asyncio.sleep(5)

    if not ready:
        raise Exception(f"Timeout chờ xử lý cho {filename}")
    if log_callback:
        log_callback(f"[{idx+1}/{total}] AI đã xử lý xong {filename}")

async def download_from_ready_tab(page, filename, download_dir, idx, total, log_callback, download_mode="free_5s"):
    """Tab đã sẵn sàng rồi thì chỉ bấm tải, không chờ ready nữa."""
    download_path = None
    if download_mode == "full":
        download_btn = page.get_by_text("Download full video", exact=False).first
    else:
        download_btn = page.get_by_text("Download 5s", exact=False).first

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    dest_path = os.path.join(download_dir, filename)

    for attempt_idx in range(3):
        try:
            await page.bring_to_front()
            # Chờ overlay loading biến mất nếu còn đang render UI
            try:
                await page.get_by_text("Loading...", exact=False).first.wait_for(state="hidden", timeout=20000)
            except Exception:
                pass

            await download_btn.scroll_into_view_if_needed(timeout=10000)
            await asyncio.sleep(0.5)
            if log_callback:
                log_callback(f"[{idx+1}/{total}] Tải {filename} (lần {attempt_idx + 1})...")
            async with page.expect_download(timeout=120000) as download_info:
                await download_btn.click(force=True)
            download = await download_info.value
            await download.save_as(dest_path)
            download_path = dest_path
            break
        except Exception as e:
            if log_callback:
                log_callback(f"[{idx+1}/{total}] Tải {filename} lỗi lần {attempt_idx + 1}: {str(e)}")
            await asyncio.sleep(1.5)

    return download_path

async def download_by_filename(page, filename, download_dir, idx, total, log_callback, download_mode="free_5s"):
    button_text = "Download full video" if download_mode == "full" else "Download 5s"
    card = page.locator("div").filter(has_text=filename).first
    btn = card.get_by_text(button_text, exact=False).first

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    dest_path = os.path.join(download_dir, filename)

    for attempt in range(3):
        try:
            async with page.expect_download(timeout=120000) as download_info:
                await btn.click(force=True)
            download = await download_info.value
            await download.save_as(dest_path)
            if log_callback:
                log_callback(f"[{idx+1}/{total}] Đã tải {filename}")
            return dest_path
        except Exception:
            await asyncio.sleep(1.5)

    raise Exception(f"Không tải được {filename}")

async def process_all_chunks(
    chunk_paths, download_dir, log_callback=None,
    progress_callback=None, download_mode="free_5s"
):
    """
    1 account, chạy theo tab theo đợt 3 video.
    Upload theo đợt và chờ xử lý xong từng đợt.
    Chỉ tải sau khi TẤT CẢ video đã ready.
    """
    processed_map = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        login_page = await context.new_page()
        await Stealth().apply_stealth_async(login_page)

        if log_callback:
            log_callback("Đang đăng nhập 1 tài khoản duy nhất...")
        await auto_login(login_page, log_callback)
        await asyncio.sleep(5)
        total = len(chunk_paths)
        state_tracker = {'completed': 0}
        batch_size = 3

        if log_callback:
            log_callback("Bắt đầu chạy theo đợt 3 video bằng tab (cuốn chiếu mỗi đợt 10 giây).")
        ready_tabs = []

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_paths = chunk_paths[batch_start:batch_end]
            batch_tabs = []

            if log_callback:
                batch_no = (batch_start // batch_size) + 1
                batch_total = (total + batch_size - 1) // batch_size
                log_callback(f"Đợt {batch_no}/{batch_total}: import {len(batch_paths)} video...")

            # Upload theo tab: video 1 xong -> chờ 1-2s -> mở tab video 2...
            for offset, path in enumerate(batch_paths):
                idx = batch_start + offset
                page, filename = await upload_chunk_in_new_tab(context, path, idx, total, log_callback)
                batch_tabs.append((idx, filename, page))
                if offset < len(batch_paths) - 1:
                    await asyncio.sleep(random.uniform(1, 2))

            # Chưa đợi ready ở đây, chỉ gom tab để check sau cùng
            ready_tabs.extend(batch_tabs)
            if log_callback:
                log_callback("Đợt này đã import xong. Chờ 10 giây rồi sang đợt tiếp theo...")

            # Tách đợt theo nhịp cố định ~10s để tiết kiệm thời gian chờ xử lý
            await asyncio.sleep(10)

        if log_callback:
            log_callback("Đã upload xong tất cả đợt. Bắt đầu check ready toàn bộ trước khi tải...")

        # Check ready toàn bộ sau khi đã upload hết
        for idx, name, tab_page in sorted(ready_tabs, key=lambda x: x[0]):
            await wait_until_ready_for_uploaded_file(
                tab_page, name, idx, total, log_callback, download_mode=download_mode
            )

        if log_callback:
            log_callback("Tất cả video đã xử lý xong. Bắt đầu tải toàn bộ...")
        await asyncio.sleep(random.uniform(3, 4))

        # Tải tuần tự trên đúng tab của từng video để tránh trùng lặp
        for idx, name, tab_page in sorted(ready_tabs, key=lambda x: x[0]):
            try:
                out = await download_from_ready_tab(
                    tab_page, name, download_dir, idx, total, log_callback, download_mode=download_mode
                )
                if out:
                    processed_map[idx] = out
                elif log_callback:
                    log_callback(f"[{idx+1}/{total}] Không tải được {name}")
            except Exception as e:
                if log_callback:
                    log_callback(f"[{idx+1}/{total}] Lỗi tải {name}: {str(e)}")
            finally:
                try:
                    await tab_page.close()
                except Exception:
                    pass
                state_tracker['completed'] += 1
                if progress_callback:
                    progress_callback(state_tracker['completed'], total)

        await context.close()
        await browser.close()
        
    # Trả về kết quả đúng thứ tự
    return [processed_map[i] for i in sorted(processed_map.keys())]
