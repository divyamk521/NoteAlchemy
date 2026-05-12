from src.transcription.youtube_downloader import YouTubeDownloader


# Example YouTube URL
url = "https://youtu.be/dQw4w9WgXcQ"


print("\n--- TEST 1: URL VALIDATION ---")

is_valid = YouTubeDownloader.is_valid_youtube_url(url)

print("Valid URL:", is_valid)


print("\n--- TEST 2: DOWNLOAD AUDIO ---")

downloader = YouTubeDownloader()

with downloader.download(url) as result:

    print("\n✅ DOWNLOAD SUCCESSFUL")

    print("Title:", result.title)
    print("Duration:", result.duration_seconds)
    print("Path:", result.path)

    print("\nChecking if file exists...")
    print(result.path.exists())

    print("\nFile size:")
    print(result.path.stat().st_size, "bytes")


print("\n--- TEST 3: CLEANUP CHECK ---")

print("File exists after context manager?")
print(result.path.exists())