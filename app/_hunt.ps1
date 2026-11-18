param(
  [int]$TargetCount = 100,
  [switch]$Quiet,
  [switch]$FetchOnly,
  [switch]$FindSources,
  [switch]$VerifyActive
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

# Work from this script's own folders (portable):
#   prox\app\_hunt.ps1  <- this script
#   prox\data\          <- all proxy data files
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $appDir
$dataDir = Join-Path $root 'data'
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
Set-Location $dataDir
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$testedPath = Join-Path $dataDir 'tested.txt'
$activePath = Join-Path $dataDir 'active.txt'
if (-not (Test-Path $testedPath)) { New-Item -ItemType File -Path $testedPath | Out-Null }

function Get-ActiveList {
  @(Get-Content $activePath -ErrorAction SilentlyContinue | Where-Object { $_ } | ForEach-Object { $_.Trim() } | Select-Object -Unique)
}
function Get-ActiveCount { (Get-ActiveList).Count }

# Already-tested set (never re-test, never duplicate)
$tested = @{}
Get-Content $testedPath -ErrorAction SilentlyContinue | ForEach-Object {
  $p = ($_ + '').Trim(); if ($p) { $tested[$p] = $true }
}
# Seed with the first batch we tested earlier
$seedNew = @()
Get-Content (Join-Path $dataDir 'proxies50.txt') -ErrorAction SilentlyContinue | ForEach-Object {
  $p = ($_ + '').Trim()
  if ($p -and -not $tested.ContainsKey($p)) { $tested[$p] = $true; $seedNew += $p }
}
if ($seedNew.Count) { Add-Content -Path $testedPath -Value $seedNew }

# ------------- VERIFY MODE -------------
# Re-tests every proxy in active.txt and REMOVES the dead ones.
# Fails get one retry pass so a temporary network blip doesn't kill a good proxy.
if ($VerifyActive) {
  $list = @(Get-ActiveList)
  $total = $list.Count
  if ($total -eq 0) {
    Write-Output "active.txt is empty - nothing to verify."
    return
  }

  Write-Output ("Verifying {0} active proxies (fails get a 2nd chance)..." -f $total)
  $survivorsPath = Join-Path $dataDir 'survivors.txt'
  $verifyFile = Join-Path $dataDir 'verify.txt'

  # Pass 1 - check the whole list
  Remove-Item $survivorsPath -ErrorAction SilentlyContinue
  Set-Content -Path $verifyFile -Value $list -Encoding ascii
  python "$appDir\PROXY CHECKER.py" verify.txt bar verify

  $alive = @()
  if (Test-Path $survivorsPath) {
    $alive = @(Get-Content $survivorsPath -ErrorAction SilentlyContinue | Where-Object { $_ } | ForEach-Object { $_.Trim() })
  }

  # Pass 2 - retry only the failures
  $aliveSet = @{}
  foreach ($p in $alive) { $aliveSet[$p] = $true }
  $failed = @($list | Where-Object { -not $aliveSet.ContainsKey($_) })
  Write-Output ("Pass 1: {0} alive, {1} failed -> retrying the failures once..." -f $alive.Count, $failed.Count)

  if ($failed.Count -gt 0) {
    Remove-Item $survivorsPath -ErrorAction SilentlyContinue
    Set-Content -Path $verifyFile -Value $failed -Encoding ascii
    python "$appDir\PROXY CHECKER.py" verify.txt bar verify
    if (Test-Path $survivorsPath) {
      $retry = @(Get-Content $survivorsPath -ErrorAction SilentlyContinue | Where-Object { $_ } | ForEach-Object { $_.Trim() })
      $alive = @($alive + $retry)
    }
  }

  # Keep original order, drop duplicates, write the cleaned list
  $keep = @{}
  foreach ($p in $alive) { $keep[$p] = $true }
  $clean = @($list | Where-Object { $keep.ContainsKey($_) })
  Set-Content -Path $activePath -Value $clean
  Remove-Item $survivorsPath, $verifyFile -ErrorAction SilentlyContinue

  $removed = $total - $clean.Count
  Write-Output ("VERIFY DONE: {0} alive, {1} dead removed. active.txt now has {2}." -f $clean.Count, $removed, $clean.Count)
  return
}

# ---------------- SOURCE POOL ----------------
$sources = @(
  @{ n='ErcinDedeoglu'; u='https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt' },
  @{ n='zevtyardt';    u='https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt' },
  @{ n='proxy4parsing';u='https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt' },
  @{ n='openproxylist';u='https://api.openproxylist.xyz/http.txt' },
  @{ n='r00tee';       u='https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt' },
  @{ n='aslisk';       u='https://raw.githubusercontent.com/aslisk/proxyhttps/main/https.txt' },
  @{ n='Ercin-https';  u='https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt' },
  @{ n='proxifly';     u='https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt' },
  @{ n='proxifly-cdn'; u='https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt' },
  @{ n='monosans';     u='https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt' },
  @{ n='TheSpeedX';    u='https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt' },
  @{ n='ProxyScrape-v2';u='https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=no&anonymity=all' },
  @{ n='ProxyScrape-v4';u='https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text' },
  @{ n='hideip.me';    u='https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt' },
  @{ n='hideip-https'; u='https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt' },
  @{ n='roosterkid';   u='https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt' },
  @{ n='sunny9577';    u='https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt' },
  @{ n='sunny-proxies';u='https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt' },
  @{ n='mmpx12';       u='https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt' },
  @{ n='jetkai';       u='https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt' },
  @{ n='proxyspace';   u='https://proxyspace.pro/http.txt' },
  @{ n='ALIILAPRO';    u='https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt' },
  @{ n='prxchk';       u='https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt' },
  @{ n='KangProxy';    u='https://raw.githubusercontent.com/officialputuid/KangProxy/main/http/http.txt' },
  @{ n='MuRongPIG';    u='https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt' },
  @{ n='vakhov-fresh'; u='https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt' },
  @{ n='spys.me';      u='https://spys.me/proxy.txt' },
  @{ n='clarketm';     u='https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt' },
  @{ n='opsxcq';       u='https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt' },
  @{ n='themiralay';   u='https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt' },
  @{ n='ShiftyTR';     u='https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt' }
)

# ------------- AUTO SOURCES (sources.txt) -------------
# Every source discovered by the auto finder is stored here as "name|url"
$sourcesFile = Join-Path $dataDir 'sources.txt'
if (Test-Path $sourcesFile) {
  Get-Content $sourcesFile -ErrorAction SilentlyContinue | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^([^|]+)\|(https?://\S+)$') {
      $nm = $Matches[1].Trim(); $u = $Matches[2].Trim()
      if ($u -and -not ($sources | Where-Object { $_.u -eq $u })) {
        $sources += @{ n = $nm; u = $u }
      }
    }
  }
}

# ------------- SOURCE FINDER -------------
function Test-SourceUrl([string]$url) {
  # Returns number of ip:port matches, or -1 on failure
  try {
    $c = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 25).Content
    return ([regex]::Matches($c, '\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}')).Count
  } catch { return -1 }
}

function Invoke-SourceFinder([int]$MaxNew = 6) {
  Write-Host "Auto source finder: searching GitHub for fresh proxy-list repos..."
  $known = @{}
  foreach ($s in $sources) { $known[$s.u] = $true }
  if (Test-Path $sourcesFile) {
    Get-Content $sourcesFile -ErrorAction SilentlyContinue | ForEach-Object {
      if ($_ -match '\|(https?://\S+)') { $known[$Matches[1]] = $true }
    }
  }

  $paths = @('http.txt','proxies/http.txt','proxies/protocols/http/data.txt','http/http.txt','all.txt')
  $repos = @()
  foreach ($q in @('proxy-list+in:name','free-proxy-list+in:name')) {
    try {
      $r = Invoke-RestMethod -Uri ("https://api.github.com/search/repositories?q={0}&sort=updated&order=desc&per_page=10" -f $q) -Headers @{ 'User-Agent' = 'proxy-finder' } -TimeoutSec 30
      $repos += @($r.items)
    } catch {
      Write-Host ("  GitHub search failed ({0})" -f ($_.Exception.Message -split "`n")[0])
    }
  }
  Write-Host ("  probing {0} recently-updated repos..." -f $repos.Count)

  $newOnes = New-Object System.Collections.Generic.List[object]
  foreach ($repo in $repos) {
    if ($newOnes.Count -ge $MaxNew) { break }
    $branch = if ($repo.default_branch) { $repo.default_branch } else { 'master' }
    foreach ($pth in $paths) {
      if ($newOnes.Count -ge $MaxNew) { break }
      $u = "https://raw.githubusercontent.com/$($repo.full_name)/$branch/$pth"
      if ($known.ContainsKey($u)) { continue }
      $n = Test-SourceUrl $u
      if ($n -ge 20) {
        $known[$u] = $true
        $newOnes.Add(@{ n = $repo.name; u = $u })
        Add-Content -Path $sourcesFile -Value ("{0}|{1}" -f $repo.name, $u)
        Write-Host ("  NEW SOURCE {0,-22} {1,6} proxies  {2}" -f $repo.name, $n, $u)
        break   # one working list per repo is enough
      }
    }
  }
  if ($newOnes.Count -eq 0) { Write-Host "  No new working sources found this time." }
  else { Write-Host ("  Added {0} new source(s) to sources.txt" -f $newOnes.Count) }
  return $newOnes.ToArray()
}

# ------------- STANDALONE FIND-SOURCES MODE -------------
if ($FindSources) {
  $newOnes = @(Invoke-SourceFinder -MaxNew 12)
  $onFile = @(Get-Content $sourcesFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '\|' }).Count
  Write-Output ("Done: {0} new source(s) added, {1} auto-discovered source(s) on file." -f $newOnes.Count, $onFile)
  return
}

# ------------- SOURCE SELECTION -------------
# How many fresh proxies does this hunt need? (~10-12% of free proxies are alive)
$needFresh = [Math]::Max(200, (($TargetCount - (Get-ActiveCount)) * 12))
$minSources =
  if     ($needFresh -le 300)  { 1 }
  elseif ($needFresh -le 1200) { 3 }
  elseif ($needFresh -le 3000) { 5 }
  else                         { $sources.Count }
Write-Output ("Need ~{0} fresh proxies -> using up to {1} of {2} sources" -f $needFresh, $minSources, $sources.Count)

$masterSet = @{}
$master = New-Object System.Collections.Generic.List[string]
function Add-Fresh([string]$p) {
  # Tolerant parser: pulls the first ip:port out of any line (works for
  # annotated lists like spys.me and plain lists alike)
  if ($p -match '(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})') {
    $cand = $Matches[1]
    if (-not $tested.ContainsKey($cand) -and -not $masterSet.ContainsKey($cand)) {
      $script:masterSet[$cand] = $true
      $script:master.Add($cand)
    }
  }
}

$fetchedUrls = @{}
$used = 0

function Invoke-SourceFetch([object[]]$list, [int]$minS, [int]$needF) {
  foreach ($s in $list) {
    if ($fetchedUrls.ContainsKey($s.u)) { continue }
    if (-not $FetchOnly -and $script:used -ge $minS -and $master.Count -ge $needF) { break }
    $fetchedUrls[$s.u] = $true
    $before = $master.Count
    try {
      $c = (Invoke-WebRequest -Uri $s.u -UseBasicParsing -TimeoutSec 40).Content
      foreach ($line in ($c -split "`r?`n")) { Add-Fresh ($line.Trim()) }
      $added = $master.Count - $before
      Write-Output ("source OK   {0,-15} (+{1})" -f $s.n, $added)
      $script:used++
    } catch {
      $msg = ($_.Exception.Message -split "`n")[0]
      Write-Output ("source FAIL {0,-15} ({1})" -f $s.n, $msg)
    }
  }
}

Invoke-SourceFetch -list $sources -minS $minSources -needF $needFresh

# Short on fresh stock? Auto-find NEW sources on GitHub and fetch them too
if (-not $FetchOnly -and $master.Count -lt $needFresh) {
  Write-Output ("Known sources gave {0} fresh (needed ~{1}) -> auto source finder starting..." -f $master.Count, $needFresh)
  $newOnes = @(Invoke-SourceFinder -MaxNew 6)
  if ($newOnes.Count -gt 0) {
    Invoke-SourceFetch -list $newOnes -minS $minSources -needF $needFresh
  }
}
Write-Output ("Fresh untested proxies available: {0}" -f $master.Count)

if ($FetchOnly) {
  Write-Output ("FETCH-ONLY mode: no proxies were checked. Active count unchanged: {0}" -f (Get-ActiveCount))
  return
}

# ------------- CHECK IN ROUNDS via PROXY CHECKER.py -------------
Write-Output ("Active at start: {0}  (target: {1})" -f (Get-ActiveCount), $TargetCount)

$round = 0
$maxRounds = [Math]::Max(15, [int][Math]::Ceiling($TargetCount / 20))
while ($true) {
  $activeNow = Get-ActiveCount
  if ($activeNow -ge $TargetCount -or $master.Count -le 0 -or $round -ge $maxRounds) { break }
  $round++
  # Right-sized batch: small asks check small batches, big asks check big ones
  $remaining = $TargetCount - $activeNow
  $chunkSize = [int][Math]::Min(300, [Math]::Max(40, $remaining * 5))
  $chunk = @($master | Select-Object -First $chunkSize)
  $master.RemoveRange(0, $chunk.Count)
  Add-Content -Path $testedPath -Value $chunk
  Set-Content -Path 'round.txt' -Value $chunk -Encoding ascii
  $t0 = Get-Date
  python "$appDir\PROXY CHECKER.py" round.txt bar
  $secs = [int]((Get-Date) - $t0).TotalSeconds
  Write-Output ("Round {0}: checked {1} in {2}s -> active total {3} (fresh left: {4})" -f $round, $chunk.Count, $secs, (Get-ActiveCount), $master.Count)
}

# Dedupe active.txt
$final = Get-ActiveList
Set-Content -Path $activePath -Value $final
Write-Output ("FINAL: {0} unique active proxies in active.txt (target was {1})" -f $final.Count, $TargetCount)
if (-not $Quiet) { $final }
