#!/usr/bin/env python3

import click
import os
import time
from transformers import pipeline
import torch

@click.command()
@click.option('--model', default='openai/whisper-base', help='ASR model to use for speech recognition. Default is "openai/whisper-base". Model sizes include base, small, medium, large, large-v2. Additionally, try appending ".en" to model names for English-only applications (not available for large).')
@click.option('--device', default='cuda:0', help='Device to use for computation. Default is "cuda:0". If you want to use CPU, specify "cpu".')
@click.option('--dtype', default='float32', help='Data type for computation. Can be either "float32" or "float16". Default is "float32".')
@click.option('--batch_size', type=int, default=8, help='Batch size for processing. This is the number of audio files processed at once. Default is 8.')
@click.option('--better_transformer', is_flag=True, help='Flag to use BetterTransformer for processing. If set, BetterTransformer will be used.')
@click.option('--task', default='transcribe', help='Type to task to execute. You can choose between {trascribe|translate}. Default is transcribe')
@click.option('--language', default='none', help='Choose the launguage. Default is none')
@click.option('--chunk_length', type=int, default=30, help='Length of audio chunks to process at once, in seconds. Default is 30 seconds.')
@click.option('--output_dir', default=os.getcwd(), help='Directory where the output files will be saved. Default is the current working directory.')
@click.option('--output_format', default='srt', help='Format of the output file. Can be "srt", "txt" or "all". Default is "srt".')
@click.argument('audio_file', type=str)

def asr_cli(model, device, dtype, batch_size, better_transformer, chunk_length, audio_file, task, language, output_format, output_dir):


    # Initialize the ASR pipeline
    pipe = pipeline("automatic-speech-recognition", 
                    model=model,
                    device=device,
                    model_kwargs = {'attn_implementation': 'sdpa'},
                    torch_dtype=torch.float16 if dtype == "float16" else torch.float32)

    if better_transformer:
        pipe.model = pipe.model.to_bettertransformer()

    # Perform ASR
    click.echo("Model loaded.")
    start_time = time.perf_counter()
    generate_kwargs = {"task": task, "language": language}
    outputs = pipe(audio_file, chunk_length_s=chunk_length, batch_size=batch_size, return_timestamps=True, generate_kwargs=generate_kwargs)

    # Output the results
    click.echo(outputs)
    click.echo("Transcription complete.")
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    click.echo(f"ASR took {elapsed_time:.2f} seconds.")

    # Save ASR chunks to output files
    audio_file_name = os.path.splitext(os.path.basename(audio_file))[0]
    formats_to_save = {output_format}        


    if not output_dir:
        save_path = audio_file
    elif output_dir.endswith('/'):
        save_path = os.path.join(output_dir, audio_file_name)
    else:
        parts = output_dir.split("/")
        new_output_name = parts[-1]
        output_dir = "/".join(parts[:-1])
        save_path = os.path.join(output_dir + "/" + new_output_name)   
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True) 
    
    match output_format:
        case'srt':
            srt_filename = f"{save_path}.srt"
            save_as_srt(srt_filename, outputs)
        case 'txt':
            txt_filename = f"{save_path}.txt"
            save_as_txt(txt_filename, outputs) 
        case 'all':
            srt_filename = f"{save_path}.srt"
            save_as_srt(srt_filename, outputs)           
            txt_filename = f"{save_path}.txt"
            save_as_txt(txt_filename, outputs) 

def seconds_to_srt_time_format(prev, seconds):
    if not (isinstance(seconds, int) or isinstance(seconds, float)):
        seconds = prev
    else:
        prev = seconds
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)
    return (prev, f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}")

def save_as_srt(srt_filename, outputs):
    with open(srt_filename, 'w', encoding="utf-8") as srt_file:
        prev = 0
        for index, chunk in enumerate(outputs['chunks']):
            prev, start_time = seconds_to_srt_time_format(prev, chunk['timestamp'][0])
            prev, end_time = seconds_to_srt_time_format(prev, chunk['timestamp'][1])
            srt_file.write(f"{index + 1}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{chunk['text'].strip()}\n\n")

def save_as_txt(txt_filename, outputs):
    with open(txt_filename, 'w', encoding="utf-8") as txt_file:
        for chunk in outputs['chunks']:
            txt_file.write(f"{chunk['text'].strip()}\n\n")


if __name__ == '__main__':
    asr_cli()