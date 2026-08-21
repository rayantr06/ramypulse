function Test-LeticiaNodeVersion {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    $versionMatch = [System.Text.RegularExpressions.Regex]::Match(
        $Version,
        '^v(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)$'
    )
    if (-not $versionMatch.Success) {
        return $false
    }

    $major = [int]$versionMatch.Groups['major'].Value
    $minor = [int]$versionMatch.Groups['minor'].Value
    $patch = [int]$versionMatch.Groups['patch'].Value
    $parsedVersion = [System.Version]::Parse("$major.$minor.$patch")

    if ($major -eq 20) {
        return $parsedVersion -ge [System.Version]'20.19.0'
    }
    if ($major -eq 22) {
        return $parsedVersion -ge [System.Version]'22.12.0'
    }

    return $false
}
