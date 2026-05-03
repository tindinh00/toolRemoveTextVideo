import os
import shutil
import asyncio
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog
from video_processor import split_video, merge_videos
from automation import process_all_chunks

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Auto Video Watermark Remover")
        self.geometry("600x550")
        
        self.input_file = None
        self.processing = False
        
        # UI Elements
        self.lbl_title = ctk.CTkLabel(self, text="Auto Video Watermark Remover", font=("Arial", 20, "bold"))
        self.lbl_title.pack(pady=20)
        
        self.btn_select = ctk.CTkButton(self, text="Chọn Video", command=self.select_video)
        self.btn_select.pack(pady=10)
        
        self.lbl_selected = ctk.CTkLabel(self, text="Chưa chọn file nào", text_color="gray")
        self.lbl_selected.pack(pady=5)
        
        self.btn_start = ctk.CTkButton(self, text="Bắt đầu xử lý", command=self.start_processing, state="disabled", fg_color="green", hover_color="darkgreen")
        self.btn_start.pack(pady=10)

        self.download_mode = ctk.StringVar(value="free_5s")
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.pack(pady=(0, 10))
        self.rb_free = ctk.CTkRadioButton(
            self.mode_frame,
            text="Free 5s (cắt + ghép)",
            variable=self.download_mode,
            value="free_5s"
        )
        self.rb_free.pack(side="left", padx=10)
        self.rb_full = ctk.CTkRadioButton(
            self.mode_frame,
            text="Download full video",
            variable=self.download_mode,
            value="full"
        )
        self.rb_full.pack(side="left", padx=10)
        
        self.lbl_progress = ctk.CTkLabel(self, text="Tiến độ: 0%")
        self.lbl_progress.pack(pady=(10, 0))
        
        self.progress = ctk.CTkProgressBar(self, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
        
        self.btn_open_folder = ctk.CTkButton(
            self, text="📂 Mở thư mục Output", 
            command=self.open_output_folder, 
            state="disabled",
            fg_color="#2980b9", hover_color="#1a5276"
        )
        self.btn_open_folder.pack(pady=(10, 0))
        
        self.log_box = ctk.CTkTextbox(self, width=500, height=200)
        self.log_box.pack(pady=10)
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
            subprocess.Popen(f'explorer "{self.output_dir_path}"')
        
    def select_video(self):
        filename = filedialog.askopenfilename(
            title="Chọn Video",
            filetypes=(("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*"))
        )
        if filename:
            self.input_file = filename
            self.lbl_selected.configure(text=os.path.basename(filename), text_color="white")
            self.btn_start.configure(state="normal")
            self.log(f"Đã chọn: {filename}")

    def start_processing(self):
        if not self.input_file or self.processing:
            return
            
        self.processing = True
        mode = self.download_mode.get()
        self.btn_select.configure(state="disabled")
        self.btn_start.configure(state="disabled")
        self.rb_free.configure(state="disabled")
        self.rb_full.configure(state="disabled")
        self.progress.set(0)
        self.lbl_progress.configure(text="Tiến độ: 0%")
        if mode == "full":
            self.log("Bắt đầu xử lý video (chế độ full video)...")
        else:
            self.log("Bắt đầu xử lý video (chế độ free 5s)...")
        
        # Start processing in a separate thread to keep UI responsive
        threading.Thread(target=self.run_workflow, daemon=True).start()
        
    def run_workflow(self):
        try:
            # 1. Setup directories
            base_dir = os.path.dirname(os.path.abspath(__file__))
            temp_dir = os.path.join(base_dir, "temp_chunks")
            processed_dir = os.path.join(base_dir, "processed_chunks")
            output_dir = os.path.join(base_dir, "output")
            
            for d in [temp_dir, processed_dir, output_dir]:
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
                os.makedirs(d)
                
            mode = self.download_mode.get()
            if mode == "full":
                # Full mode: không cắt 5s, upload trực tiếp file gốc
                self.log("Chế độ full video: bỏ qua bước cắt 5s.")
                chunk_paths = [self.input_file]
            else:
                # Free mode: cắt video thành các đoạn 5s
                self.log("Đang cắt video thành các đoạn 5s...")
                chunk_paths = split_video(self.input_file, temp_dir, chunk_duration=5)

            total_chunks = len(chunk_paths)
            self.log(f"Tổng số phần cần xử lý: {total_chunks}.")
            
            if total_chunks == 0:
                self.log("Lỗi: Không có đoạn video nào được tạo ra.")
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
                        download_mode=mode
                    )
                )
            except Exception as e:
                self.log(f"Lỗi khi chạy Playwright: {str(e)}")
                processed_paths = []
                
            loop.close()
            
            if processed_paths:
                if mode == "full":
                    output_file = os.path.join(output_dir, f"watermark_removed_{os.path.basename(self.input_file)}")
                    shutil.copy2(processed_paths[0], output_file)
                else:
                    # 4. Merge videos
                    self.log("Đang nối các đoạn video đã xử lý...")
                    output_file = os.path.join(output_dir, f"watermark_removed_{os.path.basename(self.input_file)}")
                    merge_videos(processed_paths, output_file)
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
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(processed_dir, ignore_errors=True)
            self.log("Đã dọn dẹp xong.")
            
        except Exception as e:
            self.log(f"Lỗi nghiêm trọng: {str(e)}")
        finally:
            self.processing = False
            self.btn_select.configure(state="normal")
            self.btn_start.configure(state="normal")
            self.rb_free.configure(state="normal")
            self.rb_full.configure(state="normal")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
