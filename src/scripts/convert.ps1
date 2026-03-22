$ffmpeg = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue).FullName | Select-Object -First 1
Write-Host "Found ffmpeg at $ffmpeg"
if ($ffmpeg) {
    & $ffmpeg -y -i "..\..\data\ElevenLabs_2026-03-20T16_30_39_Liam - Energetic, Social Media Creator_pre_sp100_s50_sb75_v3.mp3" -ar 16000 -ac 1 -c:a pcm_s16le ..\..\data\test_audio.wav
} else {
    Write-Host "ffmpeg not found"
}
