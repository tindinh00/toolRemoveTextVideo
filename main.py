import os
import shutil
import asyncio
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog
from workspace_ui_flow import process_all_chunks

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Công Cụ Xóa Chữ & Làm Nét Video")
        self.geometry("860x760")
        self.minsize(820, 700)
        
        self.input_file = None
        self.processing = False
        self.default_prompt = "Remove all text and watermarks from this video, and enhance the video sharpness and clarity while keeping the original content unchanged."
        self.configure(fg_color="#0b1220")
        
        # Main container
        self.main = ctk.CTkFrame(self, corner_radius=14, fg_color="#111827")
        self.main.pack(fill="both", expand=True, padx=24, pady=20)

        # Header
        self.lbl_title = ctk.CTkLabel(
            self.main,
            text="Xóa Chữ & Làm Nét Video",
            font=("SF Pro Display", 28, "bold"),
            text_color="#f8fafc"
        )
        self.lbl_title.pack(anchor="w", padx=20, pady=(18, 2))
        self.lbl_subtitle = ctk.CTkLabel(
            self.main,
            text="Quy trình: đăng nhập -> OTP/đăng ký -> upload -> prompt -> gửi -> chờ hoàn tất -> tải về",
            font=("SF Pro Text", 13),
            text_color="#94a3b8"
        )
        self.lbl_subtitle.pack(anchor="w", padx=20, pady=(0, 14))

        # Input card
        self.input_card = ctk.CTkFrame(self.main, corner_radius=12, fg_color="#0f172a")
        self.input_card.pack(fill="x", padx=20, pady=(0, 12))

        self.lbl_video = ctk.CTkLabel(
            self.input_card,
            text="Video Nguồn",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_video.pack(anchor="w", padx=14, pady=(12, 8))

        self.btn_select = ctk.CTkButton(
            self.input_card,
            text="Chọn Video",
            command=self.select_video,
            width=140,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        self.btn_select.pack(anchor="w", padx=14, pady=(0, 10))

        self.lbl_selected = ctk.CTkLabel(
            self.input_card,
            text="Chưa chọn file nào",
            text_color="#94a3b8",
            font=("SF Pro Text", 13)
        )
        self.lbl_selected.pack(anchor="w", padx=14, pady=(0, 12))

        # Prompt card
        self.prompt_card = ctk.CTkFrame(self.main, corner_radius=12, fg_color="#0f172a")
        self.prompt_card.pack(fill="x", padx=20, pady=(0, 12))

        self.lbl_prompt = ctk.CTkLabel(
            self.prompt_card,
            text="Prompt (tuỳ chỉnh)",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_prompt.pack(anchor="w", padx=14, pady=(12, 8))

        self.prompt_box = ctk.CTkTextbox(
            self.prompt_card,
            height=90,
            corner_radius=10,
            border_width=1,
            border_color="#334155",
            fg_color="#0b1220",
            text_color="#e2e8f0"
        )
        self.prompt_box.pack(fill="x", padx=14, pady=(0, 12))
        self.prompt_box.insert("1.0", self.default_prompt)

        # Actions
        self.actions = ctk.CTkFrame(self.main, fg_color="transparent")
        self.actions.pack(fill="x", padx=20, pady=(0, 12))

        self.btn_start = ctk.CTkButton(
            self.actions,
            text="Bắt Đầu Xử Lý",
            command=self.start_processing,
            state="disabled",
            width=160,
            fg_color="#16a34a",
            hover_color="#15803d"
        )
        self.btn_start.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            self.actions,
            text="Mở Thư Mục Output",
            command=self.open_output_folder,
            state="disabled",
            width=170,
            fg_color="#0ea5e9",
            hover_color="#0284c7"
        )
        self.btn_open_folder.pack(side="left", padx=(10, 0))

        # Progress
        self.progress_card = ctk.CTkFrame(self.main, corner_radius=12, fg_color="#0f172a")
        self.progress_card.pack(fill="x", padx=20, pady=(0, 12))
        self.lbl_progress = ctk.CTkLabel(self.progress_card, text="Tiến độ: 0%", text_color="#e2e8f0")
        self.lbl_progress.pack(anchor="w", padx=14, pady=(12, 8))
        self.progress = ctk.CTkProgressBar(self.progress_card, height=12)
        self.progress.pack(fill="x", padx=14, pady=(0, 12))
        self.progress.set(0)

        # Logs
        self.logs_card = ctk.CTkFrame(self.main, corner_radius=12, fg_color="#0f172a")
        self.logs_card.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        self.lbl_logs = ctk.CTkLabel(
            self.logs_card,
            text="Nhật Ký Xử Lý",
            font=("SF Pro Text", 14, "bold"),
            text_color="#e2e8f0"
        )
        self.lbl_logs.pack(anchor="w", padx=14, pady=(12, 8))
        self.log_box = ctk.CTkTextbox(
            self.logs_card,
            corner_radius=10,
            border_width=1,
            border_color="#334155",
            fg_color="#0b1220",
            text_color="#cbd5e1"
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.log_box.configure(state="disabled")
        
        self.output_dir_path = None

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        # Update Tkinter immediately
        self.update()
    
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
            self.btn_start.configure(state="normal")
            self.log(f"Đã chọn: {filename}")

    def start_processing(self):
        if not self.input_file or self.processing:
            return
            
        self.processing = True
        self.btn_select.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self.progress.set(0)
        self.lbl_progress.configure(text="Tiến độ: 0%")
        self.log("Bắt đầu quy trình: đăng nhập -> OTP/đăng ký -> upload -> prompt -> gửi -> chờ hoàn tất -> tải về...")
        
        # Start processing in a separate thread to keep UI responsive
        threading.Thread(target=self.run_workflow, daemon=True).start()
        
    def run_workflow(self):
        try:
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
                self.lbl_progress.configure(text=f"Tiến độ: {int(progress_val * 100)}%")
            
            try:
                processed_paths = loop.run_until_complete(
                    process_all_chunks(
                        chunk_paths, 
                        processed_dir, 
                        log_callback=self.log,
                        progress_callback=progress_callback,
                        prompt_text=prompt_text
                    )
                )
            except Exception as e:
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
                    self.lbl_progress.configure(text="Tiến độ: 100%")
            else:
                self.log("Không có video nào được xử lý thành công.")
                
            # 5. Cleanup
            self.log("Đang dọn dẹp file tạm...")
            shutil.rmtree(processed_dir, ignore_errors=True)
            self.log("Đã dọn dẹp xong.")
            
        except Exception as e:
            self.log(f"Lỗi nghiêm trọng: {str(e)}")
        finally:
            self.processing = False
            self.btn_select.configure(state="normal")
            self.btn_start.configure(state="normal")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
