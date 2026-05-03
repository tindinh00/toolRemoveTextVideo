import os
import math
from moviepy.editor import VideoFileClip, concatenate_videoclips

def split_video(input_path, output_dir, chunk_duration=5):
    """
    Split a video into smaller chunks of chunk_duration seconds.
    Returns a list of chunk paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    clip = VideoFileClip(input_path)
    duration = clip.duration
    chunks = math.ceil(duration / chunk_duration)
    
    chunk_paths = []
    
    for i in range(chunks):
        start_time = i * chunk_duration
        end_time = min((i + 1) * chunk_duration, duration)
        
        # Avoid creating chunks with length 0
        if end_time <= start_time:
            break
            
        subclip = clip.subclip(start_time, end_time)
        
        chunk_name = f"chunk_{i:03d}.mp4"
        chunk_path = os.path.join(output_dir, chunk_name)
        
        # Write file with libx264 codec and aac audio
        subclip.write_videofile(
            chunk_path, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile=os.path.join(output_dir, f"temp_audio_{i}.m4a"),
            remove_temp=True,
            logger=None
        )
        chunk_paths.append(chunk_path)
        
    clip.close()
    return chunk_paths

def merge_videos(video_paths, output_path):
    """
    Merge multiple video clips into one.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir) and output_dir != '':
        os.makedirs(output_dir)
        
    clips = []
    for path in sorted(video_paths):
        clips.append(VideoFileClip(path))
        
    if not clips:
        return
        
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac",
        logger=None
    )
    
    # Close clips to release resources
    for clip in clips:
        clip.close()
    final_clip.close()
