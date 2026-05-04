import os
import shutil
import asyncio
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from workspace_ui_flow import process_all_chunks, test_workspace_selectors

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Công Cụ Xóa Chữ & Làm Nét Video")
        self.geometry("1180x820")
        self.minsize(980, 700)
        
        self.input_file = None
        self.processing = False
        self.default_prompt = "Remove all text and watermarks from this video, and enhance the video sharpness and clarity while keeping the original content unchanged."
        self.configure(fg_color="#0b1220")
        self.log_file_path = None
        self.log_file_handle = None
        self.cancel_requested = False
        self.retry_after_cancel = False
        
        # Main container
        self.main = ctk.CTkFrame(self, corner_radius=16, fg_color="#111827")
        self.main.pack(fill="both", expand=True, padx=28, pady=24)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self.main, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 14))
        self.header.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self.header,
            text="Xóa Chữ & Làm Nét Video",
            font=("SF Pro Display", 28, "bold"),
            text_color="#f8fafc"
        )
        self.lbl_title.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.lbl_subtitle = ctk.CTkLabel(
            self.header,
            text="Quy trình: đăng nhập -> OTP/đăng ký -> upload -> prompt -> gửi -> chờ hoàn tất -> tải về",
            font=("SF Pro Text", 13),
            text_color="#94a3b8"
        )
        self.lbl_subtitle.grid(row=1, column=0, sticky="w")

        # Content row (2-column split)
        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1, minsize=420)
        self.content.grid_columnconfigure(1, weight=1, minsize=420)

        # Left column
        self.left_col = ctk.CTkFrame(self.content, corner_radius=0, fg_color="transparent")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(24, 12), pady=(0, 20))
        self.left_col.grid_columnconfigure(0, weight=1)
        self.left_col.grid_rowconfigure(0, weight=1)

        self.input_card = ctk.CTkFrame(self.left_col, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1f2937")
        self.input_card.grid(row=0, column=0, sticky="nsew")
        self.input_card.grid_columnconfigure(0, weight=1)

        self.lbl_video = ctk.CTkLabel(
            self.input_card,
            text="Input",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_video.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.video_preview = ctk.CTkFrame(
            self.input_card,
            corner_radius=12,
            fg_color="#0b1220",
            border_width=1,
            border_color="#334155",
            height=250
        )
        self.video_preview.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.video_preview.grid_propagate(False)
        self.video_preview.grid_columnconfigure(0, weight=1)
        self.video_preview.grid_rowconfigure(0, weight=1)

        self.lbl_preview = ctk.CTkLabel(
            self.video_preview,
            text="Video Preview Placeholder",
            text_color="#64748b",
            font=("SF Pro Text", 13)
        )
        self.lbl_preview.grid(row=0, column=0)

        self.btn_select = ctk.CTkButton(
            self.input_card,
            text="Chọn Video",
            command=self.select_video,
            width=140,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        self.btn_select.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        self.lbl_selected = ctk.CTkLabel(
            self.input_card,
            text="Chưa chọn file nào",
            text_color="#94a3b8",
            font=("SF Pro Text", 13)
        )
        self.lbl_selected.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 12))

        self.lbl_prompt = ctk.CTkLabel(
            self.input_card,
            text="Prompt (tuỳ chỉnh)",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_prompt.grid(row=4, column=0, sticky="w", padx=16, pady=(2, 8))

        self.prompt_box = ctk.CTkTextbox(
            self.input_card,
            height=130,
            corner_radius=10,
            border_width=1,
            border_color="#334155",
            fg_color="#0b1220",
            text_color="#e2e8f0"
        )
        self.prompt_box.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.prompt_box.insert("1.0", self.default_prompt)

        # Right column
        self.right_col = ctk.CTkFrame(self.content, corner_radius=0, fg_color="transparent")
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 24), pady=(0, 20))
        self.right_col.grid_columnconfigure(0, weight=1)
        self.right_col.grid_rowconfigure(4, weight=1)

        self.actions = ctk.CTkFrame(self.right_col, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1f2937")
        self.actions.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.actions.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            self.actions,
            text="Bắt Đầu Xử Lý",
            command=self.start_processing,
            state="disabled",
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
            corner_radius=10,
            text_color="#ecfdf5",
            text_color_disabled="#bbf7d0"
        )
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))

        self.btn_retry = ctk.CTkButton(
            self.actions,
            text="Retry (Bỏ Qua Đăng Nhập)",
            command=self.retry_processing,
            state="disabled",
            fg_color="transparent",
            border_width=1,
            border_color="#f59e0b",
            hover_color="#3f2c08",
            text_color="#fbbf24",
            text_color_disabled="#fcd34d",
            height=34
        )
        self.btn_retry.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.btn_test_selectors = ctk.CTkButton(
            self.actions,
            text="Kiểm Tra Selector",
            command=self.test_selectors,
            fg_color="transparent",
            border_width=1,
            border_color="#8b5cf6",
            hover_color="#25163f",
            text_color="#c4b5fd",
            text_color_disabled="#ddd6fe",
            height=34
        )
        self.btn_test_selectors.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.btn_open_folder = ctk.CTkButton(
            self.actions,
            text="Mở Thư Mục Output",
            command=self.open_output_folder,
            state="disabled",
            fg_color="transparent",
            border_width=1,
            border_color="#22d3ee",
            hover_color="#123544",
            text_color="#67e8f9",
            text_color_disabled="#a5f3fc",
            height=34
        )
        self.btn_open_folder.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

        # Progress
        self.progress_card = ctk.CTkFrame(self.right_col, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1f2937")
        self.progress_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.progress_card.grid_columnconfigure(0, weight=1)
        self.lbl_progress = ctk.CTkLabel(self.progress_card, text="Tiến độ: 0%", text_color="#e2e8f0")
        self.lbl_progress.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))
        self.progress = ctk.CTkProgressBar(
            self.progress_card,
            height=10,
            progress_color="#0ea5e9",
            fg_color="#1e293b"
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.progress.set(0)

        self.segment_row = ctk.CTkFrame(self.progress_card, fg_color="transparent")
        self.segment_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.progress_segments = []
        for idx in range(20):
            self.segment_row.grid_columnconfigure(idx, weight=1)
            seg = ctk.CTkFrame(self.segment_row, height=6, corner_radius=8, fg_color="#1e293b")
            seg.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 2, 0))
            self.progress_segments.append(seg)
        self._render_segmented_progress(0)

        # Runtime config collapsible
        self.cfg_card = ctk.CTkFrame(self.right_col, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1f2937")
        self.cfg_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.cfg_card.grid_columnconfigure(0, weight=1)
        self.cfg_header = ctk.CTkFrame(self.cfg_card, fg_color="transparent")
        self.cfg_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 8))
        self.cfg_header.grid_columnconfigure(0, weight=1)
        self.lbl_cfg = ctk.CTkLabel(self.cfg_header, text="Cấu Hình Thời Gian / Retry", text_color="#e2e8f0", font=("SF Pro Text", 13, "bold"))
        self.lbl_cfg.grid(row=0, column=0, sticky="w")
        self.btn_cfg_toggle = ctk.CTkButton(
            self.cfg_header,
            text="⚙",
            width=28,
            height=28,
            corner_radius=8,
            fg_color="#1f2937",
            hover_color="#334155",
            command=self.toggle_runtime_config
        )
        self.btn_cfg_toggle.grid(row=0, column=1, sticky="e")

        self.cfg_content = ctk.CTkFrame(self.cfg_card, fg_color="transparent")

        self.auto_close_var = ctk.BooleanVar(value=False)
        self.auto_close_switch = ctk.CTkSwitch(
            self.cfg_content,
            text="Tự đóng Chrome khi xong",
            variable=self.auto_close_var,
            onvalue=True,
            offvalue=False
        )
        self.auto_close_switch.pack(anchor="w", padx=2, pady=(0, 8))

        self.cfg_row = ctk.CTkFrame(self.cfg_content, fg_color="transparent")
        self.cfg_row.pack(fill="x", padx=2, pady=(0, 10))
        self.cfg_row.grid_columnconfigure(1, weight=1)
        self.cfg_row.grid_columnconfigure(3, weight=1)

        self.lbl_otp = ctk.CTkLabel(self.cfg_row, text="OTP timeout (giây):")
        self.lbl_otp.grid(row=0, column=0, sticky="w")
        self.entry_otp = ctk.CTkEntry(self.cfg_row, width=84)
        self.entry_otp.insert(0, "120")
        self.entry_otp.grid(row=0, column=1, sticky="w", padx=(6, 12))

        self.lbl_mission = ctk.CTkLabel(self.cfg_row, text="Mission timeout (giây):")
        self.lbl_mission.grid(row=0, column=2, sticky="w")
        self.entry_mission = ctk.CTkEntry(self.cfg_row, width=92)
        self.entry_mission.insert(0, "1200")
        self.entry_mission.grid(row=0, column=3, sticky="w", padx=(6, 0))

        self.lbl_retry = ctk.CTkLabel(self.cfg_row, text="Số vòng retry download:")
        self.lbl_retry.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.entry_retry = ctk.CTkEntry(self.cfg_row, width=84)
        self.entry_retry.insert(0, "50")
        self.entry_retry.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        self.cfg_open = False

        # Logs
        self.logs_card = ctk.CTkFrame(self.right_col, corner_radius=14, fg_color="#0f172a", border_width=1, border_color="#1f2937")
        self.logs_card.grid(row=4, column=0, sticky="nsew")
        self.logs_card.grid_columnconfigure(0, weight=1)
        self.logs_card.grid_rowconfigure(1, weight=1)
        self.lbl_logs = ctk.CTkLabel(
            self.logs_card,
            text="Nhật Ký Xử Lý",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_logs.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))
        self.log_box = ctk.CTkTextbox(
            self.logs_card,
            corner_radius=10,
            border_width=1,
            border_color="#334155",
            fg_color="#0b1220",
            text_color="#cbd5e1",
            wrap="word"
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.log_box.configure(state="disabled")
        
        self.output_dir_path = None

    def toggle_runtime_config(self):
        if self.cfg_open:
            self.cfg_content.grid_forget()
            self.cfg_open = False
            return
        self.cfg_content.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.cfg_open = True

    def _render_segmented_progress(self, progress_value):
        filled_count = int(max(0, min(1, progress_value)) * len(self.progress_segments))
        for i, segment in enumerate(self.progress_segments):
            color = "#0ea5e9" if i < filled_count else "#1e293b"
            segment.configure(fg_color=color)

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        if self.log_file_handle is not None:
            self.log_file_handle.write(message + "\n")
            self.log_file_handle.flush()
        # Update Tkinter immediately
        self.update()

    def _open_log_file(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file_path = os.path.join(logs_dir, f"run-{ts}.log")
        self.log_file_handle = open(self.log_file_path, "a", encoding="utf-8")
        self.log(f"Tệp log: {self.log_file_path}")

    def _close_log_file(self):
        if self.log_file_handle is not None:
            try:
                self.log_file_handle.close()
            except Exception:
                pass
        self.log_file_handle = None
    
    def open_output_folder(self):
        if self.output_dir_path and os.path.exists(self.output_dir_path):
            if os.name == "nt":
                subprocess.Popen(f'explorer "{self.output_dir_path}"')
            else:
                subprocess.Popen(["open", self.output_dir_path])
        
    def select_video(self):
        filename = filedialog.askopenfilename(
            title="Chọn Video",
            filetypes=(("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*"))
        )
        if filename:
            self.input_file = filename
            self.lbl_selected.configure(text=os.path.basename(filename), text_color="#e2e8f0")
            self.lbl_preview.configure(text=f"Đã chọn video:\n{os.path.basename(filename)}", text_color="#93c5fd")
            self.btn_start.configure(state="normal")
            self.log(f"Đã chọn: {filename}")

    def start_processing(self):
        if not self.input_file or self.processing:
            return
            
        self.processing = True
        self.btn_select.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="normal")
        self.btn_test_selectors.configure(state="disabled")
        self.progress.set(0)
        self._render_segmented_progress(0)
        self.lbl_progress.configure(text="Tiến độ: 0%")
        self._open_log_file()
        self.log("Bắt đầu quy trình: đăng nhập -> OTP/đăng ký -> upload -> prompt -> gửi -> chờ hoàn tất -> tải về...")
        
        # Start processing in a separate thread to keep UI responsive
        threading.Thread(target=self.run_workflow, kwargs={"skip_auth": False}, daemon=True).start()

    def retry_processing(self):
        if not self.input_file:
            return

        if self.processing:
            if self.retry_after_cancel:
                self.log("Retry đã được xếp hàng, vui lòng chờ luồng hiện tại dừng...")
                return
            self.cancel_requested = True
            self.retry_after_cancel = True
            self.log("Đã nhận lệnh Retry: dừng luồng hiện tại...")
            return

        # Bắt đầu lượt retry mới: reset cờ hủy/xếp hàng cũ.
        self.cancel_requested = False
        self.retry_after_cancel = False
        self.processing = True
        self.btn_select.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="normal")
        self.btn_test_selectors.configure(state="disabled")
        self.progress.set(0)
        self._render_segmented_progress(0)
        self.lbl_progress.configure(text="Tiến độ: 0%")
        self._open_log_file()
        self.log("Retry: dùng lại session browser hiện tại, bỏ qua login/regis nếu còn hiệu lực...")
        self.log("Đang khởi động luồng Retry mới...")
        threading.Thread(target=self.run_workflow, kwargs={"skip_auth": True}, daemon=True).start()

    def test_selectors(self):
        if self.processing:
            return
        self.processing = True
        self.btn_select.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="disabled")
        self.btn_test_selectors.configure(state="disabled")
        self._open_log_file()
        self.log("Bắt đầu test selectors...")
        threading.Thread(target=self.run_selector_test, daemon=True).start()

    def run_selector_test(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            otp_timeout_sec = int(self.entry_otp.get().strip() or "120")
            ok = loop.run_until_complete(
                asyncio.wait_for(
                    test_workspace_selectors(
                        log_callback=self.log,
                        skip_auth=True,
                        otp_timeout_sec=otp_timeout_sec,
                    ),
                    timeout=180
                )
            )
            self.log("Kết quả test selectors: " + ("OK" if ok else "FAIL"))
            loop.close()
        except asyncio.TimeoutError:
            self.log("Lỗi test selectors: Timeout quá 180s.")
        except Exception as e:
            self.log(f"Lỗi test selectors: {str(e)}")
        finally:
            self.processing = False
            self.btn_select.configure(state="normal")
            self.btn_start.configure(state="normal")
            self.btn_retry.configure(state="normal" if self.input_file else "disabled")
            self.btn_test_selectors.configure(state="normal")
            self._close_log_file()
        
    def run_workflow(self, skip_auth=False):
        try:
            self.cancel_requested = False
            # 1. Setup directories
            base_dir = os.path.dirname(os.path.abspath(__file__))
            processed_dir = os.path.join(base_dir, "processed_chunks")
            output_dir = os.path.join(base_dir, "output")
            
            for d in [processed_dir, output_dir]:
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
                os.makedirs(d)
                
            self.log("Đã khởi tạo workflow.")
            chunk_paths = [self.input_file]
            prompt_text = self.prompt_box.get("1.0", "end-1c").strip()
            otp_timeout_sec = int(self.entry_otp.get().strip() or "120")
            mission_timeout_sec = int(self.entry_mission.get().strip() or "1200")
            download_retry_rounds = int(self.entry_retry.get().strip() or "50")

            total_chunks = len(chunk_paths)
            self.log(f"Số mục cần xử lý: {total_chunks}.")
            
            if total_chunks == 0:
                self.log("Lỗi: không tìm thấy video đầu vào.")
                return

            # 3. Process chunks with Playwright
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            def progress_callback(current, total):
                progress_val = current / total
                self.progress.set(progress_val)
                self._render_segmented_progress(progress_val)
                self.lbl_progress.configure(text=f"Tiến độ: {int(progress_val * 100)}%")
            
            try:
                processed_paths = loop.run_until_complete(
                    process_all_chunks(
                        chunk_paths, 
                        processed_dir, 
                        log_callback=self.log,
                        progress_callback=progress_callback,
                        prompt_text=prompt_text,
                        skip_auth=skip_auth,
                        auto_close_browser=self.auto_close_var.get(),
                        otp_timeout_sec=otp_timeout_sec,
                        mission_timeout_sec=mission_timeout_sec,
                        download_retry_rounds=download_retry_rounds,
                        cancel_check=lambda: self.cancel_requested,
                    )
                )
            except Exception as e:
                if "WORKFLOW_CANCELLED_BY_RETRY" in str(e):
                    self.log("Đã dừng workflow hiện tại theo lệnh Retry.")
                else:
                    self.log(f"Lỗi khi chạy Playwright: {str(e)}")
                processed_paths = []
                
            loop.close()
            
            if processed_paths:
                output_file = os.path.join(output_dir, f"watermark_removed_{os.path.basename(self.input_file)}")
                shutil.copy2(processed_paths[0], output_file)
                self.log(f"Hoàn tất! Video đã lưu tại: {output_file}")
                
                # Lưu đường dẫn và bật nút mở thư mục
                self.output_dir_path = output_dir
                self.btn_open_folder.configure(state="normal")
                
                # Make sure progress is 100% if we processed all chunks successfully
                if len(processed_paths) == total_chunks:
                    self.progress.set(1.0)
                    self._render_segmented_progress(1.0)
                    self.lbl_progress.configure(text="Tiến độ: 100%")
            else:
                self.log("Không có video nào được xử lý thành công.")
                
            # 5. Dọn dẹp
            self.log("Đang dọn dẹp file tạm...")
            shutil.rmtree(processed_dir, ignore_errors=True)
            self.log("Đã dọn dẹp xong.")
            
        except Exception as e:
            self.log(f"Lỗi nghiêm trọng: {str(e)}")
        finally:
            self.processing = False
            self.btn_select.configure(state="normal")
            self.btn_start.configure(state="normal")
            self.btn_retry.configure(state="normal" if self.input_file else "disabled")
            self.btn_test_selectors.configure(state="normal")
            self._close_log_file()
            if self.retry_after_cancel:
                self.retry_after_cancel = False
                self.retry_processing()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
